from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.resume_extraction_service import resume_extraction_service
from app.core.config import settings
from app.db.session import async_session_factory
from app.models.candidate import Candidate, CandidateEducation, CandidateEmployment, CandidateSkill
from app.models.resume import Resume, ResumeProcessingJob, UploadBatch
from app.services.docx_extractor_service import docx_extractor
from app.services.duplicate_detection_service import duplicate_detector
from app.services.pdf_extractor_service import pdf_extractor
from app.services.storage_service import get_storage_service
from app.services.text_normalization_service import text_normalizer

logger = logging.getLogger("shortlistai.worker")


class ResumeWorkerService:
    """
    Background worker service that polls and processes resume ingestion jobs
    from the persistent PostgreSQL queue with row-level claiming and bounded concurrency.
    """

    def __init__(self, concurrency: int = 5, lock_timeout_seconds: int = 600, session_factory=None) -> None:
        self.concurrency = concurrency
        self.lock_timeout_seconds = lock_timeout_seconds
        self._semaphore = asyncio.Semaphore(concurrency)
        self._running = False
        self.session_factory = session_factory or async_session_factory

    async def claim_next_job(self, db: AsyncSession, worker_id: str) -> Optional[ResumeProcessingJob]:
        """
        Atomically claim the next pending or timed-out processing job.
        Uses optimistic concurrency with status and lock_id check.
        """
        now = datetime.now(timezone.utc)
        timeout_threshold = now - timedelta(seconds=self.lock_timeout_seconds)

        # Select candidate job: either pending, or stuck in processing past lock timeout
        stmt = (
            select(ResumeProcessingJob)
            .where(
                or_(
                    ResumeProcessingJob.status == "pending",
                    (
                        (ResumeProcessingJob.status == "processing")
                        & (ResumeProcessingJob.locked_at < timeout_threshold)
                        & (ResumeProcessingJob.attempt_count < ResumeProcessingJob.max_attempts)
                    ),
                )
            )
            .order_by(ResumeProcessingJob.created_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )

        result = await db.execute(stmt)
        job = result.scalars().first()

        if not job:
            return None

        # Claim the job
        job.status = "processing"
        job.lock_id = worker_id
        job.locked_at = now
        job.started_at = now
        job.attempt_count += 1
        await db.commit()
        await db.refresh(job)
        return job

    async def process_job_by_id(self, job_id: uuid.UUID) -> bool:
        """Process a specific job by ID in an isolated database session."""
        async with self.session_factory() as db:
            result = await db.execute(
                select(ResumeProcessingJob).where(ResumeProcessingJob.id == job_id)
            )
            job = result.scalars().first()
            if not job:
                return False

            return await self.execute_job(db, job)

    async def execute_job(self, db: AsyncSession, job: ResumeProcessingJob) -> bool:
        """Execute the parsing pipeline for a single claimed job."""
        resume_id = job.resume_id
        batch_id = job.batch_id
        org_id = job.organization_id

        # Load Resume
        resume_res = await db.execute(select(Resume).where(Resume.id == resume_id))
        resume = resume_res.scalars().first()
        if not resume:
            job.status = "failed"
            job.last_error_code = "RESUME_NOT_FOUND"
            job.last_error_message = "Associated resume record missing."
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()
            return False

        try:
            storage = get_storage_service()

            # 1. Text Extraction (if not already extracted)
            if resume.extraction_status != "extracted":
                resume.extraction_status = "extracting"
                resume.parse_status = "processing"
                await db.commit()

                file_bytes = await storage.get_file(resume.storage_path)

                if resume.file_name.lower().endswith(".pdf") or resume.mime_type == "application/pdf":
                    extract_res = pdf_extractor.extract_text(file_bytes)
                else:
                    extract_res = docx_extractor.extract_text(file_bytes)

                if not extract_res.success:
                    resume.extraction_status = extract_res.status
                    resume.parse_status = "needs_review" if extract_res.status == "ocr_required" else "failed"
                    resume.error_code = extract_res.error_code
                    resume.error_message_safe = extract_res.error_message
                    resume.processed_at = datetime.now(timezone.utc)

                    job.status = "completed" if extract_res.status == "ocr_required" else "failed"
                    job.last_error_code = extract_res.error_code
                    job.last_error_message = extract_res.error_message
                    job.completed_at = datetime.now(timezone.utc)

                    await db.commit()
                    await self._update_batch_stats(db, batch_id)
                    return True

                resume.raw_text = extract_res.raw_text
                resume.normalized_text = text_normalizer.normalize(extract_res.raw_text)
                resume.extraction_status = "extracted"
                await db.commit()

            # 2. Level 3 Content Similarity Check (if not already marked duplicate)
            if not resume.duplicate_of_id and resume.normalized_text:
                sim_res = await duplicate_detector.check_content_similarity(
                    db=db,
                    organization_id=org_id,
                    normalized_text=resume.normalized_text,
                    exclude_resume_id=resume.id,
                )
                if sim_res.is_duplicate:
                    resume.duplicate_of_id = sim_res.existing_resume_id
                    resume.duplicate_type = sim_res.duplicate_type
                    resume.duplicate_details = sim_res.details
                    resume.parse_status = "duplicate"
                    if sim_res.existing_candidate_id:
                        resume.candidate_id = sim_res.existing_candidate_id

            # 3. AI / Deterministic Structured Profile Extraction
            extraction_result = await resume_extraction_service.extract_candidate_profile(
                resume.normalized_text or resume.raw_text or ""
            )

            # 4. Level 2 Candidate Matching & Association
            matched_candidate_id = resume.candidate_id
            if not matched_candidate_id:
                cand_match = await duplicate_detector.check_candidate_match(
                    db=db,
                    organization_id=org_id,
                    email=extraction_result.email,
                    phone=extraction_result.phone,
                )
                if cand_match.is_duplicate and cand_match.existing_candidate_id:
                    matched_candidate_id = cand_match.existing_candidate_id
                    if not resume.duplicate_type:
                        resume.duplicate_type = cand_match.duplicate_type
                        resume.duplicate_details = cand_match.details

            candidate: Optional[Candidate] = None
            if matched_candidate_id:
                c_res = await db.execute(select(Candidate).where(Candidate.id == matched_candidate_id))
                candidate = c_res.scalars().first()

            if not candidate:
                # Create a new candidate record
                candidate = Candidate(
                    organization_id=org_id,
                    full_name=extraction_result.full_name or resume.file_name,
                    email=extraction_result.email,
                    phone=extraction_result.phone,
                    location=extraction_result.location,
                    notice_period_days=extraction_result.notice_period_days,
                    total_experience_years=extraction_result.total_experience_years,
                    certifications=[c.model_dump() for c in extraction_result.certifications],
                    parsed_profile_json=extraction_result.model_dump(),
                )
                db.add(candidate)
                await db.flush()

                # Add structured employment entries
                for emp in extraction_result.employment_history:
                    db.add(
                        CandidateEmployment(
                            candidate_id=candidate.id,
                            company=emp.company,
                            job_title=emp.job_title,
                            start_date=emp.start_date,
                            end_date=emp.end_date,
                            is_current=emp.is_current,
                            description=emp.description,
                            technologies=emp.technologies,
                        )
                    )

                # Add structured education entries
                for edu in extraction_result.education:
                    db.add(
                        CandidateEducation(
                            candidate_id=candidate.id,
                            institution=edu.institution,
                            qualification=edu.qualification,
                            field_of_study=edu.field_of_study,
                            graduation_year=edu.graduation_year,
                        )
                    )

                # Add structured skill entries
                for sk in extraction_result.skills:
                    db.add(
                        CandidateSkill(
                            candidate_id=candidate.id,
                            name=sk.name,
                            raw_name=sk.raw_name,
                            evidence=sk.evidence,
                        )
                    )

                # Record default consent tracking for recruitment processing
                from app.models.audit import ConsentRecord
                db.add(
                    ConsentRecord(
                        id=uuid.uuid4(),
                        candidate_id=candidate.id,
                        organization_id=org_id,
                        uploaded_by=resume.uploaded_by or candidate.id,
                        legal_basis="CONSENT",
                        privacy_notice_acknowledged=True,
                        status="GRANTED",
                        purpose="resume_screening_and_shortlisting",
                        version="v1.0",
                        collection_method="DIRECT_UPLOAD_NOTICE",
                        requisition_id=resume.requisition_id,
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                    )
                )

            resume.candidate_id = candidate.id

            # Determine final parse_status
            if resume.parse_status != "duplicate":
                if extraction_result.warnings and not extraction_result.full_name and not extraction_result.email:
                    resume.parse_status = "needs_review"
                else:
                    resume.parse_status = "parsed"

            resume.processed_at = datetime.now(timezone.utc)
            resume.error_code = None
            resume.error_message_safe = None

            # Mark job completed
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            job.last_error_code = None
            job.last_error_message = None

            await db.commit()
            await self._update_batch_stats(db, batch_id)
            return True

        except Exception as e:
            logger.exception("Error processing resume job %s", job.id)
            await db.rollback()

            # Retry handling
            async with self.session_factory() as err_db:
                j_res = await err_db.execute(
                    select(ResumeProcessingJob).where(ResumeProcessingJob.id == job.id)
                )
                curr_job = j_res.scalars().first()
                r_res = await err_db.execute(select(Resume).where(Resume.id == resume_id))
                curr_resume = r_res.scalars().first()

                if curr_job:
                    if curr_job.attempt_count < curr_job.max_attempts:
                        curr_job.status = "pending"
                        curr_job.last_error_code = "TRANSIENT_ERROR"
                        curr_job.last_error_message = str(e)
                    else:
                        curr_job.status = "failed"
                        curr_job.completed_at = datetime.now(timezone.utc)
                        curr_job.last_error_code = "MAX_ATTEMPTS_EXCEEDED"
                        curr_job.last_error_message = f"Failed after {curr_job.attempt_count} attempts: {str(e)}"

                        if curr_resume:
                            curr_resume.parse_status = "failed"
                            curr_resume.error_code = "PROCESSING_FAILED"
                            curr_resume.error_message_safe = "Processing failed after maximum retry attempts."
                            curr_resume.processed_at = datetime.now(timezone.utc)

                    await err_db.commit()
                    await self._update_batch_stats(err_db, batch_id)

            return False

    async def _update_batch_stats(self, db: AsyncSession, batch_id: uuid.UUID) -> None:
        """Atomically aggregate and update upload_batch counts and overall status."""
        # Query counts of all resumes in this batch
        q = (
            select(
                Resume.parse_status,
                func.count(Resume.id).label("count"),
            )
            .where(Resume.upload_batch_id == batch_id)
            .group_by(Resume.parse_status)
        )
        res = await db.execute(q)
        status_counts = dict(res.all())

        parsed_count = status_counts.get("parsed", 0) + status_counts.get("needs_review", 0)
        duplicate_count = status_counts.get("duplicate", 0)
        failed_count = status_counts.get("failed", 0)
        processing_count = status_counts.get("processing", 0) + status_counts.get("pending", 0)
        total_finished = parsed_count + duplicate_count + failed_count

        b_res = await db.execute(select(UploadBatch).where(UploadBatch.id == batch_id))
        batch = b_res.scalars().first()
        if not batch:
            return

        batch.completed_files = parsed_count
        batch.processed = parsed_count
        batch.duplicate_files = duplicate_count
        batch.duplicates = duplicate_count
        batch.failed_files = failed_count
        batch.failed = failed_count
        batch.processing_files = processing_count

        if processing_count == 0:
            batch.completed_at = datetime.now(timezone.utc)
            if failed_count == 0:
                batch.status = "completed"
            elif total_finished == failed_count:
                batch.status = "failed"
            else:
                batch.status = "partial_failure"
        else:
            batch.status = "processing"

        await db.commit()

    async def process_batch_jobs(self, batch_id: uuid.UUID) -> None:
        """
        Process all pending jobs in a given batch.
        Useful for deterministic testing and synchronous runs.
        """
        async with self.session_factory() as db:
            q = (
                select(ResumeProcessingJob)
                .where(
                    ResumeProcessingJob.batch_id == batch_id,
                    ResumeProcessingJob.status == "pending",
                )
                .order_by(ResumeProcessingJob.created_at.asc())
            )
            res = await db.execute(q)
            jobs = res.scalars().all()

        for j in jobs:
            await self.process_job_by_id(j.id)

    async def run_worker_loop(self, poll_interval: float = 1.0) -> None:
        """Continuous background worker loop for standalone execution."""
        worker_id = f"worker-{uuid.uuid4()}"
        self._running = True
        logger.info("Starting ResumeWorkerService loop with worker_id %s", worker_id)

        while self._running:
            try:
                async with self.session_factory() as db:
                    job = await self.claim_next_job(db, worker_id)

                if job:
                    async with self._semaphore:
                        await self.process_job_by_id(job.id)
                else:
                    await asyncio.sleep(poll_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Error in worker loop: %s", e)
                await asyncio.sleep(poll_interval)

    def stop(self) -> None:
        self._running = False


worker_service = ResumeWorkerService(
    concurrency=settings.WORKER_CONCURRENCY,
    lock_timeout_seconds=settings.WORKER_LOCK_TIMEOUT_SECONDS,
)
