from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.candidate import Candidate, CandidateSkill
from app.models.organization import OrganizationMembership
from app.models.requisition import Requisition
from app.models.resume import Resume, ResumeProcessingJob, UploadBatch
from app.models.user import User
from app.repositories.resume_repository import resume_repository
from app.services.document_validation_service import validation_service
from app.services.duplicate_detection_service import duplicate_detector
from app.services.storage_service import get_storage_service
from app.services.worker_service import worker_service

logger = logging.getLogger("shortlistai.services.resume")


class ResumeService:
    """Business logic for resume bulk uploads, parsing management, and authorized downloads."""

    async def _verify_org_access(
        self,
        db: AsyncSession,
        user: User,
        organization_id: uuid.UUID,
        allowed_roles: Optional[List[str]] = None,
    ) -> str:
        """Verify user membership and role within organization."""
        q = select(OrganizationMembership).where(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.is_active == True,
        )
        res = await db.execute(q)
        membership = res.scalars().first()
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not an active member of this organization.",
            )

        if allowed_roles and membership.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{membership.role}' lacks permission for this action.",
            )
        return membership.role

    async def upload_resumes(
        self,
        db: AsyncSession,
        requisition_id: uuid.UUID,
        user: User,
        files: List[UploadFile],
    ) -> UploadBatch:
        # 1. Verify Requisition exists and retrieve its organization
        req_res = await db.execute(select(Requisition).where(Requisition.id == requisition_id))
        requisition = req_res.scalars().first()
        if not requisition:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requisition not found.")

        org_id = requisition.organization_id
        await self._verify_org_access(
            db, user, org_id, allowed_roles=["recruiter", "delivery_head", "super_admin", "admin"]
        )

        # 2. Check batch limits
        if not files or len(files) == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No files provided for upload.")

        if len(files) > settings.MAX_BATCH_FILES_COUNT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Batch file count ({len(files)}) exceeds maximum limit of {settings.MAX_BATCH_FILES_COUNT}.",
            )

        storage = get_storage_service()

        # 3. Create UploadBatch
        batch = UploadBatch(
            organization_id=org_id,
            recruiter_id=user.id,
            requisition_id=requisition_id,
            total_files=len(files),
            status="processing",
        )
        db.add(batch)
        await db.flush()

        accepted_count = 0
        rejected_count = 0
        duplicate_count = 0
        total_batch_bytes = 0
        jobs_to_trigger: List[uuid.UUID] = []

        # 4. Stream and process each file
        for upload_file in files:
            content = await upload_file.read()
            file_size = len(content)
            total_batch_bytes += file_size

            if total_batch_bytes > settings.MAX_BATCH_SIZE_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Total batch size exceeds maximum limit of {settings.MAX_BATCH_SIZE_BYTES / (1024*1024):.0f} MB.",
                )

            filename = upload_file.filename or "unnamed_resume"
            client_mime = upload_file.content_type

            # Validation
            val_res = validation_service.validate_file(filename, content, client_mime)

            if not val_res.is_valid:
                rejected_count += 1
                resume = Resume(
                    organization_id=org_id,
                    requisition_id=requisition_id,
                    uploaded_by=user.id,
                    file_name=filename[:255],
                    storage_path="none",
                    file_hash=val_res.sha256_hash,
                    mime_type=val_res.detected_mime,
                    file_size_bytes=val_res.file_size_bytes,
                    parse_status="failed",
                    extraction_status="failed",
                    error_code=val_res.error_code,
                    error_message_safe=val_res.error_message_safe,
                    upload_batch_id=batch.id,
                    processed_at=datetime.now(timezone.utc),
                )
                db.add(resume)
                continue

            # Save file to storage
            ext = "." + filename.rsplit(".", 1)[-1] if "." in filename else ".bin"
            storage_key = await storage.save_file(org_id, content, ext)

            # Check Level 1 exact file duplicate
            exact_dup = await duplicate_detector.check_exact_file_duplicate(
                db=db,
                organization_id=org_id,
                file_hash=val_res.sha256_hash,
            )

            if exact_dup.is_duplicate:
                duplicate_count += 1
                resume = Resume(
                    organization_id=org_id,
                    requisition_id=requisition_id,
                    uploaded_by=user.id,
                    file_name=filename[:255],
                    storage_path=storage_key,
                    file_hash=val_res.sha256_hash,
                    mime_type=val_res.detected_mime,
                    file_size_bytes=val_res.file_size_bytes,
                    parse_status="duplicate",
                    extraction_status="extracted",
                    duplicate_of_id=exact_dup.existing_resume_id,
                    duplicate_type="exact_file",
                    duplicate_details=exact_dup.details,
                    candidate_id=exact_dup.existing_candidate_id,
                    upload_batch_id=batch.id,
                    processed_at=datetime.now(timezone.utc),
                )
                db.add(resume)
                continue

            # Valid new resume: create Resume and Queue Job
            accepted_count += 1
            resume = Resume(
                organization_id=org_id,
                requisition_id=requisition_id,
                uploaded_by=user.id,
                file_name=filename[:255],
                storage_path=storage_key,
                file_hash=val_res.sha256_hash,
                mime_type=val_res.detected_mime,
                file_size_bytes=val_res.file_size_bytes,
                parse_status="pending",
                extraction_status="pending",
                upload_batch_id=batch.id,
            )
            db.add(resume)
            await db.flush()

            job = ResumeProcessingJob(
                resume_id=resume.id,
                batch_id=batch.id,
                organization_id=org_id,
                status="pending",
            )
            db.add(job)
            await db.flush()
            jobs_to_trigger.append(job.id)

        # Update batch summary
        batch.accepted_files = accepted_count
        batch.rejected_files = rejected_count
        batch.duplicate_files = duplicate_count
        batch.duplicates = duplicate_count
        batch.failed_files = rejected_count
        batch.failed = rejected_count
        batch.processing_files = accepted_count

        if accepted_count == 0:
            batch.status = "completed" if duplicate_count > 0 else "failed"
            batch.completed_at = datetime.now(timezone.utc)
        else:
            batch.status = "processing"

        await db.commit()
        await db.refresh(batch)

        # Trigger background processing for pending jobs
        if jobs_to_trigger:
            for j_id in jobs_to_trigger:
                asyncio.create_task(worker_service.process_job_by_id(j_id))

        return batch

    async def get_batch(self, db: AsyncSession, batch_id: uuid.UUID, user: User) -> UploadBatch:
        q = select(UploadBatch).where(UploadBatch.id == batch_id)
        res = await db.execute(q)
        batch = res.scalars().first()
        if not batch:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload batch not found.")

        await self._verify_org_access(db, user, batch.organization_id)
        return batch

    async def get_batch_files(
        self, db: AsyncSession, batch_id: uuid.UUID, user: User
    ) -> List[Resume]:
        batch = await self.get_batch(db, batch_id, user)
        return await resume_repository.get_resumes_by_batch(db, batch_id, batch.organization_id)

    async def get_resume(self, db: AsyncSession, resume_id: uuid.UUID, user: User) -> Resume:
        resume = await resume_repository.get_resume_by_id(db, resume_id)
        if not resume:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found.")

        await self._verify_org_access(db, user, resume.organization_id)
        return resume

    async def download_resume(
        self, db: AsyncSession, resume_id: uuid.UUID, user: User
    ) -> Tuple[bytes, str, str]:
        resume = await self.get_resume(db, resume_id, user)

        # Check role permission: clients cannot download raw candidate resumes
        role = await self._verify_org_access(
            db, user, resume.organization_id, allowed_roles=["recruiter", "delivery_head", "super_admin", "admin"]
        )

        if not resume.storage_path or resume.storage_path == "none":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume file is not available.")

        storage = get_storage_service()
        try:
            file_bytes = await storage.get_file(resume.storage_path)
            return file_bytes, resume.file_name, resume.mime_type
        except Exception as e:
            logger.error("Failed to read resume file from storage: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve resume file from storage.",
            )

    async def retry_resume(self, db: AsyncSession, resume_id: uuid.UUID, user: User) -> Resume:
        resume = await self.get_resume(db, resume_id, user)
        await self._verify_org_access(
            db, user, resume.organization_id, allowed_roles=["recruiter", "delivery_head", "super_admin", "admin"]
        )

        if resume.parse_status not in ("failed", "needs_review"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Resume with status '{resume.parse_status}' is not eligible for retry.",
            )

        # Reset resume state
        resume.parse_status = "pending"
        resume.error_code = None
        resume.error_message_safe = None

        # Check for existing job or create new one
        q_job = select(ResumeProcessingJob).where(ResumeProcessingJob.resume_id == resume_id)
        res_job = await db.execute(q_job)
        job = res_job.scalars().first()

        if job:
            job.status = "pending"
            job.attempt_count = 0
            job.last_error_code = None
            job.last_error_message = None
            job.started_at = None
            job.completed_at = None
        else:
            job = ResumeProcessingJob(
                resume_id=resume.id,
                batch_id=resume.upload_batch_id or uuid.uuid4(),
                organization_id=resume.organization_id,
                status="pending",
            )
            db.add(job)

        await db.commit()
        await db.refresh(resume)

        # Trigger worker
        asyncio.create_task(worker_service.process_job_by_id(job.id))
        return resume

    async def review_resume(
        self,
        db: AsyncSession,
        resume_id: uuid.UUID,
        user: User,
        full_name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        location: Optional[str] = None,
        notice_period_days: Optional[int] = None,
        skills: Optional[List[str]] = None,
    ) -> Resume:
        resume = await self.get_resume(db, resume_id, user)
        await self._verify_org_access(
            db, user, resume.organization_id, allowed_roles=["recruiter", "delivery_head", "super_admin", "admin"]
        )

        # Update associated candidate
        if resume.candidate_id:
            c_res = await db.execute(select(Candidate).where(Candidate.id == resume.candidate_id))
            candidate = c_res.scalars().first()
            if candidate:
                if full_name is not None:
                    candidate.full_name = full_name
                if email is not None:
                    candidate.email = email
                if phone is not None:
                    candidate.phone = phone
                if location is not None:
                    candidate.location = location
                if notice_period_days is not None:
                    candidate.notice_period_days = notice_period_days

                if skills is not None:
                    # Clear existing skills and insert new ones
                    await db.execute(
                        select(CandidateSkill).where(CandidateSkill.candidate_id == candidate.id)
                    )
                    # Add newly specified skills
                    for s_name in skills:
                        clean_s = s_name.strip()
                        if clean_s:
                            db.add(
                                CandidateSkill(
                                    candidate_id=candidate.id,
                                    name=clean_s.lower(),
                                    raw_name=clean_s,
                                    evidence="Recruiter manual entry",
                                )
                            )

        resume.parse_status = "parsed"
        resume.error_code = None
        resume.error_message_safe = None
        await db.commit()
        await db.refresh(resume)
        return resume


resume_service = ResumeService()

