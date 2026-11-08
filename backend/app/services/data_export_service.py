from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.audit import ConsentRecord, DataRequest
from app.models.candidate import (
    Candidate,
    CandidateEducation,
    CandidateEmployment,
    CandidateSkill,
)
from app.models.evaluation import Evaluation, EvaluationEvidence, RecruiterReview
from app.models.resume import Resume
from app.models.submission import Submission
from app.services.audit_service import log_event
from app.services.storage_service import LocalStorageService


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def create_data_request(
    db: AsyncSession,
    candidate_id: uuid.UUID,
    organization_id: uuid.UUID,
    requested_by: uuid.UUID,
    request_type: str = "EXPORT",
    reason: Optional[str] = None,
) -> DataRequest:
    """Creates a new candidate personal data access or export request."""
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

    req = DataRequest(
        id=uuid.uuid4(),
        candidate_id=candidate_id,
        organization_id=organization_id,
        requested_by=requested_by,
        request_type=request_type.upper(),
        status="PENDING",
        created_at=datetime.now(timezone.utc),
    )
    db.add(req)

    await log_event(
        db=db,
        organization_id=organization_id,
        actor_user_id=requested_by,
        event_type="DATA_ACCESS_REQUESTED",
        resource_type="candidate",
        resource_id=candidate_id,
        payload={
            "data_request_id": str(req.id),
            "request_type": request_type.upper(),
            "reason": reason,
        },
    )

    await db.commit()
    await db.refresh(req)
    return req


async def generate_candidate_export(
    db: AsyncSession,
    request_id: uuid.UUID,
    organization_id: uuid.UUID,
) -> Dict[str, Any]:
    """Compiles and exports all authorized personal candidate records to structured JSON."""
    res = await db.execute(
        select(DataRequest).where(
            DataRequest.id == request_id,
            DataRequest.organization_id == organization_id,
        )
    )
    request = res.scalar_one_or_none()
    if not request:
        raise ValueError("Data request not found")

    candidate_id = request.candidate_id

    # Fetch candidate with employments, educations, skills
    cand_res = await db.execute(
        select(Candidate)
        .options(
            selectinload(Candidate.employments),
            selectinload(Candidate.educations),
            selectinload(Candidate.skills),
        )
        .where(
            Candidate.id == candidate_id,
            Candidate.organization_id == organization_id,
        )
    )
    candidate = cand_res.scalar_one_or_none()
    if not candidate:
        raise ValueError("Candidate not found")

    # Fetch resumes
    resume_res = await db.execute(
        select(Resume).where(
            Resume.candidate_id == candidate_id,
            Resume.organization_id == organization_id,
        )
    )
    resumes = resume_res.scalars().all()

    # Fetch evaluations
    eval_res = await db.execute(
        select(Evaluation)
        .options(
            selectinload(Evaluation.evidence),
            selectinload(Evaluation.reviews),
        )
        .where(Evaluation.candidate_id == candidate_id)
    )
    evaluations = eval_res.scalars().all()

    # Fetch submissions
    sub_res = await db.execute(
        select(Submission).where(
            Submission.candidate_id == candidate_id,
            Submission.source_organization_id == organization_id,
        )
    )
    submissions = sub_res.scalars().all()

    # Fetch consent records
    consent_res = await db.execute(
        select(ConsentRecord)
        .where(
            ConsentRecord.candidate_id == candidate_id,
            ConsentRecord.organization_id == organization_id,
        )
        .order_by(desc(ConsentRecord.created_at))
    )
    consent_records = consent_res.scalars().all()

    now = datetime.now(timezone.utc)

    # Build export payload
    export_payload: Dict[str, Any] = {
        "export_id": str(request.id),
        "exported_at": now.isoformat(),
        "candidate_id": str(candidate.id),
        "organization_id": str(organization_id),
        "profile": {
            "full_name": candidate.full_name,
            "email": candidate.email,
            "phone": candidate.phone,
            "location": candidate.location,
            "notice_period_days": candidate.notice_period_days,
            "total_experience_years": float(candidate.total_experience_years) if candidate.total_experience_years else None,
            "certifications": candidate.certifications,
            "created_at": candidate.created_at.isoformat() if candidate.created_at else None,
            "is_anonymized": candidate.is_anonymized,
            "consent_status": candidate.consent_status,
        },
        "employments": [
            {
                "company": e.company,
                "job_title": e.job_title,
                "start_date": e.start_date,
                "end_date": e.end_date,
                "is_current": e.is_current,
                "description": e.description,
                "technologies": e.technologies,
            }
            for e in candidate.employments
        ],
        "educations": [
            {
                "institution": ed.institution,
                "qualification": ed.qualification,
                "field_of_study": ed.field_of_study,
                "graduation_year": ed.graduation_year,
            }
            for ed in candidate.educations
        ],
        "skills": [
            {
                "name": s.name,
                "raw_name": s.raw_name,
                "evidence": s.evidence,
            }
            for s in candidate.skills
        ],
        "resumes": [
            {
                "file_name": r.file_name,
                "mime_type": r.mime_type,
                "file_size_bytes": r.file_size_bytes,
                "file_hash": r.file_hash,
                "parse_status": r.parse_status,
                "extraction_status": r.extraction_status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in resumes
        ],
        "evaluations": [
            {
                "id": str(ev.id),
                "requisition_id": str(ev.requisition_id),
                "total_score": float(ev.total_score) if ev.total_score else None,
                "normalized_score": float(ev.normalized_score) if ev.normalized_score else None,
                "evidence_coverage": float(ev.evidence_coverage) if ev.evidence_coverage else None,
                "confidence_level": ev.confidence_level,
                "created_at": ev.created_at.isoformat() if ev.created_at else None,
                "evidence": [
                    {
                        "status": item.evidence_status,
                        "confidence_score": float(item.confidence_score) if item.confidence_score else None,
                        "source_excerpts": item.source_excerpts_json,
                    }
                    for item in (ev.evidence or [])
                ],
            }
            for ev in evaluations
        ],
        "recruiter_reviews": [
            {
                "evaluation_id": str(ev.id),
                "decision": rev.decision,
                "notes": rev.notes,
                "reviewed_at": rev.reviewed_at.isoformat() if rev.reviewed_at else None,
            }
            for ev in evaluations
            for rev in (ev.reviews or [])
        ],
        "submissions": [
            {
                "id": str(sub.id),
                "requisition_id": str(sub.requisition_id),
                "current_stage": sub.current_stage,
                "status": sub.status,
                "created_at": sub.created_at.isoformat() if sub.created_at else None,
            }
            for sub in submissions
        ],
        "consent_history": [
            {
                "id": str(c.id),
                "purpose": c.purpose,
                "status": c.status,
                "version": c.version,
                "collection_method": c.collection_method,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "withdrawn_at": c.withdrawn_at.isoformat() if c.withdrawn_at else None,
            }
            for c in consent_records
        ],
        "processing_status": {
            "is_anonymized": candidate.is_anonymized,
            "consent_status": candidate.consent_status,
            "deletion_status": candidate.deletion_status,
        },
        "excluded_fields_notice": (
            "The following categories of data are excluded from this export: "
            "internal system credentials, authentication tokens, physical server storage paths, "
            "internal recruiter notes, proprietary scorecard weighting constants, and other candidates' data."
        ),
    }

    # Write export to private storage
    storage_root = Path(getattr(settings, "STORAGE_LOCAL_ROOT", "./storage/private")) / "exports"
    full_path = storage_root / str(organization_id) / str(candidate_id) / f"{request.id}.json"
    full_path.parent.mkdir(parents=True, exist_ok=True)

    json_bytes = json.dumps(export_payload, indent=2).encode("utf-8")
    with open(full_path, "wb") as f:
        f.write(json_bytes)

    # Update request
    expires_at = now + timedelta(days=7)
    request.status = "COMPLETED"
    request.export_file_path = str(full_path)
    request.completed_at = now
    request.expires_at = expires_at
    request.export_metadata = {
        "file_size_bytes": len(json_bytes),
        "employments_count": len(candidate.employments),
        "educations_count": len(candidate.educations),
        "skills_count": len(candidate.skills),
        "evaluations_count": len(evaluations),
    }

    await log_event(
        db=db,
        organization_id=organization_id,
        actor_user_id=request.requested_by,
        event_type="DATA_EXPORT_GENERATED",
        resource_type="candidate",
        resource_id=candidate_id,
        payload={
            "data_request_id": str(request.id),
            "file_size_bytes": len(json_bytes),
            "expires_at": expires_at.isoformat(),
        },
    )

    await db.commit()
    await db.refresh(request)
    return export_payload


async def get_data_request(
    db: AsyncSession,
    request_id: uuid.UUID,
    organization_id: uuid.UUID,
) -> Optional[DataRequest]:
    """Retrieves a data request scoped to the organization."""
    res = await db.execute(
        select(DataRequest).where(
            DataRequest.id == request_id,
            DataRequest.organization_id == organization_id,
        )
    )
    return res.scalar_one_or_none()


async def list_data_requests(
    db: AsyncSession,
    organization_id: uuid.UUID,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[DataRequest], int]:
    """Lists data requests for an organization."""
    query = select(DataRequest).where(DataRequest.organization_id == organization_id)
    if status:
        query = query.where(DataRequest.status == status.upper())

    count_res = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_res.scalar_one()

    paginated_query = query.order_by(desc(DataRequest.created_at)).offset(offset).limit(limit)
    res = await db.execute(paginated_query)
    records = list(res.scalars().all())

    return records, total


async def download_data_export(
    db: AsyncSession,
    request_id: uuid.UUID,
    organization_id: uuid.UUID,
    actor_id: Optional[uuid.UUID] = None,
) -> Tuple[bytes, str]:
    """Reads export file and logs download audit event."""
    request = await get_data_request(db, request_id, organization_id)
    if not request:
        raise ValueError("Export request not found")
    if request.status != "COMPLETED" or not request.export_file_path:
        raise ValueError("Export file is not ready or has failed")

    now = datetime.now(timezone.utc)
    if request.expires_at and ensure_utc(request.expires_at) < now:
        request.status = "EXPIRED"
        await db.commit()
        raise ValueError("Export download link has expired")

    file_path = Path(request.export_file_path)
    if not file_path.exists():
        raise ValueError("Export file was not found in storage")

    content = file_path.read_bytes()

    await log_event(
        db=db,
        organization_id=organization_id,
        actor_user_id=actor_id,
        event_type="DATA_EXPORT_DOWNLOADED",
        resource_type="data_request",
        resource_id=request_id,
        payload={
            "file_size_bytes": len(content),
            "candidate_id": str(request.candidate_id),
        },
        commit=True,
    )

    filename = f"candidate_export_{request.candidate_id}_{request.id.hex[:6]}.json"
    return content, filename
