from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.audit import DeletionRequest
from app.models.candidate import Candidate
from app.models.resume import Resume, ResumeProcessingJob
from app.services.audit_service import log_event
from app.services.storage_service import LocalStorageService


async def create_deletion_request(
    db: AsyncSession,
    candidate_id: uuid.UUID,
    organization_id: uuid.UUID,
    requested_by: uuid.UUID,
    reason: Optional[str] = None,
) -> DeletionRequest:
    """Initiates a formal candidate deletion request."""
    # Verify candidate belongs to organization
    res = await db.execute(
        select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.organization_id == organization_id,
        )
    )
    candidate = res.scalar_one_or_none()
    if not candidate:
        raise ValueError("Candidate not found in this organization")

    # Check for active deletion request
    existing_res = await db.execute(
        select(DeletionRequest).where(
            DeletionRequest.candidate_id == candidate_id,
            DeletionRequest.organization_id == organization_id,
            DeletionRequest.status.in_(["REQUESTED", "UNDER_REVIEW", "APPROVED", "SCHEDULED"]),
        )
    )
    existing = existing_res.scalar_one_or_none()
    if existing:
        return existing

    req = DeletionRequest(
        id=uuid.uuid4(),
        candidate_id=candidate_id,
        organization_id=organization_id,
        requested_by=requested_by,
        reason=reason,
        status="REQUESTED",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(req)

    candidate.deletion_status = "PENDING_DELETION"
    candidate.updated_at = datetime.now(timezone.utc)

    await log_event(
        db=db,
        organization_id=organization_id,
        actor_user_id=requested_by,
        event_type="DELETION_REQUESTED",
        resource_type="candidate",
        resource_id=candidate_id,
        payload={
            "deletion_request_id": str(req.id),
            "reason": reason,
        },
    )

    await db.commit()
    await db.refresh(req)
    return req


async def review_deletion_request(
    db: AsyncSession,
    request_id: uuid.UUID,
    organization_id: uuid.UUID,
    reviewer_id: uuid.UUID,
    decision: str,
    review_notes: Optional[str] = None,
    retention_policy_notes: Optional[str] = None,
    is_legal_hold: bool = False,
    legal_hold_reason: Optional[str] = None,
) -> DeletionRequest:
    """Reviews and updates the approval or hold status of a deletion request."""
    norm_decision = decision.upper()
    if norm_decision not in ("APPROVE", "REJECT", "HOLD"):
        raise ValueError("Decision must be APPROVE, REJECT, or HOLD")

    res = await db.execute(
        select(DeletionRequest).where(
            DeletionRequest.id == request_id,
            DeletionRequest.organization_id == organization_id,
        )
    )
    req = res.scalar_one_or_none()
    if not req:
        raise ValueError("Deletion request not found")

    cand_res = await db.execute(select(Candidate).where(Candidate.id == req.candidate_id))
    candidate = cand_res.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    req.reviewer_id = reviewer_id
    req.review_decision = norm_decision
    req.review_notes = review_notes
    req.retention_policy_notes = retention_policy_notes
    req.updated_at = now

    if is_legal_hold or norm_decision == "HOLD":
        req.is_legal_hold = True
        req.legal_hold_reason = legal_hold_reason or "Active legal or regulatory hold"
        req.status = "UNDER_REVIEW"
        if candidate:
            candidate.deletion_status = "RETENTION_HOLD"
            candidate.updated_at = now
    elif norm_decision == "APPROVE":
        req.status = "APPROVED"
        req.is_legal_hold = False
        if candidate:
            candidate.deletion_status = "APPROVED_FOR_DELETION"
            candidate.updated_at = now
    elif norm_decision == "REJECT":
        req.status = "REJECTED"
        req.is_legal_hold = False
        if candidate:
            candidate.deletion_status = None
            candidate.updated_at = now

    await log_event(
        db=db,
        organization_id=organization_id,
        actor_user_id=reviewer_id,
        event_type="DELETION_REVIEWED",
        resource_type="deletion_request",
        resource_id=req.id,
        payload={
            "decision": norm_decision,
            "is_legal_hold": req.is_legal_hold,
            "legal_hold_reason": req.legal_hold_reason,
            "retention_policy_notes": retention_policy_notes,
        },
    )

    await db.commit()
    await db.refresh(req)
    return req


async def execute_deletion(
    db: AsyncSession,
    request_id: uuid.UUID,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> Dict[str, Any]:
    """Safely and idempotently executes an approved deletion request."""
    res = await db.execute(
        select(DeletionRequest).where(
            DeletionRequest.id == request_id,
            DeletionRequest.organization_id == organization_id,
        )
    )
    req = res.scalar_one_or_none()
    if not req:
        raise ValueError("Deletion request not found")

    if req.is_legal_hold:
        raise ValueError(f"Deletion blocked by legal hold: {req.legal_hold_reason or 'Legal hold active'}")

    if req.status not in ("APPROVED", "SCHEDULED", "COMPLETED"):
        raise ValueError(f"Cannot execute deletion: request status is {req.status}. Must be APPROVED.")

    cand_res = await db.execute(
        select(Candidate).where(
            Candidate.id == req.candidate_id,
            Candidate.organization_id == organization_id,
        )
    )
    candidate = cand_res.scalar_one_or_none()
    if not candidate:
        raise ValueError("Candidate not found")

    now = datetime.now(timezone.utc)
    deleted_files_count = 0
    storage = LocalStorageService()

    # 1. Locate and delete all uploaded resume files
    resume_res = await db.execute(
        select(Resume).where(
            Resume.candidate_id == candidate.id,
            Resume.organization_id == organization_id,
        )
    )
    resumes = resume_res.scalars().all()

    for r in resumes:
        if r.storage_path:
            try:
                # Delete from physical storage
                file_path = Path(r.storage_path)
                if file_path.exists():
                    os.remove(file_path)
                    deleted_files_count += 1
            except Exception:
                pass

        # Scrub raw and normalized text from database
        r.raw_text = None
        r.normalized_text = None
        r.parse_error = None
        r.storage_path = "[FILE_DELETED]"

        # Cancel any active or pending background jobs
        jobs_res = await db.execute(
            select(ResumeProcessingJob).where(ResumeProcessingJob.resume_id == r.id)
        )
        for job in jobs_res.scalars().all():
            if job.status in ("pending", "processing"):
                job.status = "cancelled"
                job.error_message = "Cancelled due to candidate deletion request"

    # 2. Anonymize candidate PII
    candidate.full_name = "[DELETED]"
    candidate.email = None
    candidate.phone = None
    candidate.location = "[DELETED]"
    candidate.parsed_profile_json = None
    candidate.certifications = None
    candidate.is_anonymized = True
    candidate.consent_status = "WITHDRAWN"
    candidate.deletion_status = "COMPLETED"
    candidate.updated_at = now

    # 3. Update deletion request
    req.status = "COMPLETED"
    req.files_deleted_count = deleted_files_count
    req.completed_at = now
    req.updated_at = now

    # 4. Record audit event
    await log_event(
        db=db,
        organization_id=organization_id,
        actor_user_id=actor_id,
        event_type="DELETION_EXECUTED",
        resource_type="candidate",
        resource_id=candidate.id,
        payload={
            "deletion_request_id": str(req.id),
            "files_deleted_count": deleted_files_count,
            "anonymized": True,
        },
    )

    await db.commit()
    await db.refresh(req)

    return {
        "deletion_request_id": req.id,
        "candidate_id": candidate.id,
        "status": "COMPLETED",
        "files_deleted_count": deleted_files_count,
        "anonymized": True,
        "completed_at": now,
        "message": f"Successfully deleted {deleted_files_count} file(s) and anonymized candidate personal data.",
    }


async def get_deletion_request(
    db: AsyncSession,
    request_id: uuid.UUID,
    organization_id: uuid.UUID,
) -> Optional[DeletionRequest]:
    """Retrieves a deletion request scoped to organization."""
    res = await db.execute(
        select(DeletionRequest).where(
            DeletionRequest.id == request_id,
            DeletionRequest.organization_id == organization_id,
        )
    )
    return res.scalar_one_or_none()


async def list_deletion_requests(
    db: AsyncSession,
    organization_id: uuid.UUID,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[DeletionRequest], int]:
    """Lists deletion requests for an organization."""
    query = select(DeletionRequest).where(DeletionRequest.organization_id == organization_id)
    if status:
        query = query.where(DeletionRequest.status == status.upper())

    count_res = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_res.scalar_one()

    paginated_query = query.order_by(desc(DeletionRequest.created_at)).offset(offset).limit(limit)
    res = await db.execute(paginated_query)
    records = list(res.scalars().all())

    return records, total
