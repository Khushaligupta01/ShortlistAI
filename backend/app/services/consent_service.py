from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import ConsentRecord
from app.models.candidate import Candidate
from app.models.organization import Organization
from app.services.audit_service import log_event


def hash_token(raw_token: str) -> str:
    """Computes a SHA-256 hash of a raw token."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def get_candidate_reference(candidate: Candidate) -> str:
    """Generates synthetic candidate identifier."""
    hex_suffix = candidate.id.hex[:5].upper()
    return f"Candidate CND-{hex_suffix}"


async def create_consent_request(
    db: AsyncSession,
    candidate_id: uuid.UUID,
    organization_id: uuid.UUID,
    recruiter_id: uuid.UUID,
    purpose: str = "resume_screening_and_shortlisting",
    collection_method: str = "PUBLIC_LINK",
    requisition_id: Optional[uuid.UUID] = None,
) -> Tuple[ConsentRecord, str]:
    """Initiates a candidate consent request and produces a secure expiring token."""
    # Validate candidate belongs to organization
    res = await db.execute(
        select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.organization_id == organization_id,
        )
    )
    candidate = res.scalar_one_or_none()
    if not candidate:
        raise ValueError("Candidate not found in this organization")

    # Generate secure random token
    raw_token = secrets.token_urlsafe(32)
    token_hashed = hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=14)

    consent_record = ConsentRecord(
        id=uuid.uuid4(),
        candidate_id=candidate_id,
        organization_id=organization_id,
        uploaded_by=recruiter_id,
        legal_basis="CONSENT",
        privacy_notice_acknowledged=True,
        status="PENDING",
        purpose=purpose,
        version="v1.0",
        collection_method=collection_method,
        requisition_id=requisition_id,
        token_hash=token_hashed,
        token_expires_at=expires_at,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(consent_record)

    candidate.consent_status = "PENDING"
    await db.flush()

    # Log audit event
    await log_event(
        db=db,
        organization_id=organization_id,
        actor_user_id=recruiter_id,
        event_type="CONSENT_REQUESTED",
        resource_type="candidate",
        resource_id=candidate_id,
        payload={
            "consent_record_id": str(consent_record.id),
            "purpose": purpose,
            "collection_method": collection_method,
            "expires_at": expires_at.isoformat(),
        },
    )

    await db.commit()
    await db.refresh(consent_record)
    return consent_record, raw_token


async def get_public_consent_info(
    db: AsyncSession,
    raw_token: str,
) -> Dict[str, Any]:
    """Retrieves safe public information for a candidate consent decision link."""
    token_hashed = hash_token(raw_token)
    res = await db.execute(
        select(ConsentRecord, Candidate, Organization)
        .join(Candidate, ConsentRecord.candidate_id == Candidate.id)
        .join(Organization, ConsentRecord.organization_id == Organization.id)
        .where(ConsentRecord.token_hash == token_hashed)
    )
    row = res.first()
    if not row:
        raise ValueError("Invalid or unknown consent token")

    consent_record, candidate, org = row

    now = datetime.now(timezone.utc)
    is_expired = consent_record.token_expires_at and ensure_utc(consent_record.token_expires_at) < now
    is_valid = consent_record.status == "PENDING" and not is_expired and consent_record.used_at is None

    return {
        "token": raw_token,
        "candidate_reference": get_candidate_reference(candidate),
        "organization_name": org.name,
        "purpose": consent_record.purpose,
        "version": consent_record.version,
        "token_expires_at": consent_record.token_expires_at,
        "status": consent_record.status,
        "is_valid": is_valid,
    }


async def record_candidate_consent_decision(
    db: AsyncSession,
    raw_token: str,
    decision: str,
    reason: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> ConsentRecord:
    """Records a candidate's consent decision (GRANTED or DECLINED)."""
    norm_decision = decision.upper()
    if norm_decision not in ("GRANTED", "DECLINED"):
        raise ValueError("Decision must be GRANTED or DECLINED")

    token_hashed = hash_token(raw_token)
    res = await db.execute(
        select(ConsentRecord).where(ConsentRecord.token_hash == token_hashed)
    )
    record = res.scalar_one_or_none()
    if not record:
        raise ValueError("Invalid consent token")

    now = datetime.now(timezone.utc)
    if record.used_at is not None:
        raise ValueError("Consent token has already been used")
    if record.token_expires_at and ensure_utc(record.token_expires_at) < now:
        record.status = "EXPIRED"
        await db.commit()
        raise ValueError("Consent token has expired")

    # Fetch candidate
    cand_res = await db.execute(select(Candidate).where(Candidate.id == record.candidate_id))
    candidate = cand_res.scalar_one_or_none()

    record.status = norm_decision
    record.used_at = now
    record.updated_at = now
    if reason:
        record.withdrawal_reason = reason
    if ip_address:
        record.ip_hash = hashlib.sha256(ip_address.encode()).hexdigest()
    if user_agent:
        record.user_agent = user_agent[:255]

    if candidate:
        candidate.consent_status = norm_decision
        candidate.updated_at = now

    event_type = "CONSENT_GRANTED" if norm_decision == "GRANTED" else "CONSENT_DECLINED"
    await log_event(
        db=db,
        organization_id=record.organization_id,
        actor_user_id=None,
        event_type=event_type,
        resource_type="candidate",
        resource_id=record.candidate_id,
        payload={
            "consent_record_id": str(record.id),
            "decision": norm_decision,
            "has_reason": bool(reason),
        },
    )

    await db.commit()
    await db.refresh(record)
    return record


async def withdraw_candidate_consent(
    db: AsyncSession,
    candidate_id: uuid.UUID,
    organization_id: uuid.UUID,
    actor_id: Optional[uuid.UUID] = None,
    reason: Optional[str] = None,
) -> ConsentRecord:
    """Withdraws consent for a candidate, preventing future processing."""
    # Find candidate
    cand_res = await db.execute(
        select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.organization_id == organization_id,
        )
    )
    candidate = cand_res.scalar_one_or_none()
    if not candidate:
        raise ValueError("Candidate not found in this organization")

    now = datetime.now(timezone.utc)

    # Find latest consent record
    res = await db.execute(
        select(ConsentRecord)
        .where(
            ConsentRecord.candidate_id == candidate_id,
            ConsentRecord.organization_id == organization_id,
        )
        .order_by(desc(ConsentRecord.created_at))
    )
    record = res.scalars().first()

    if not record:
        # Create a withdrawal record
        record = ConsentRecord(
            id=uuid.uuid4(),
            candidate_id=candidate_id,
            organization_id=organization_id,
            uploaded_by=actor_id or candidate.id,
            legal_basis="CONSENT",
            privacy_notice_acknowledged=True,
            status="WITHDRAWN",
            purpose="resume_screening_and_shortlisting",
            version="v1.0",
            collection_method="WITHDRAWAL_REQUEST",
            withdrawn_at=now,
            withdrawal_reason=reason,
            created_at=now,
            updated_at=now,
        )
        db.add(record)
    else:
        record.status = "WITHDRAWN"
        record.withdrawn_at = now
        record.withdrawal_reason = reason
        record.updated_at = now

    candidate.consent_status = "WITHDRAWN"
    candidate.updated_at = now

    await log_event(
        db=db,
        organization_id=organization_id,
        actor_user_id=actor_id,
        event_type="CONSENT_WITHDRAWN",
        resource_type="candidate",
        resource_id=candidate_id,
        payload={
            "consent_record_id": str(record.id),
            "reason": reason,
        },
    )

    await db.commit()
    await db.refresh(record)
    return record


def is_processing_allowed(candidate: Candidate) -> Tuple[bool, str]:
    """Validates whether processing (AI evaluation, client submission) is legally authorized."""
    if candidate.is_anonymized or candidate.deletion_status == "DELETED":
        return False, "Candidate data has been deleted or anonymized under a deletion request"

    status = (candidate.consent_status or "GRANTED").upper()
    if status == "WITHDRAWN":
        return False, "Candidate consent has been withdrawn"
    if status == "DECLINED":
        return False, "Candidate declined consent for data processing"
    if status == "PENDING":
        return False, "Candidate consent request is currently pending"

    return True, "Processing authorized"


async def get_candidate_consent_records(
    db: AsyncSession,
    candidate_id: uuid.UUID,
    organization_id: uuid.UUID,
) -> List[ConsentRecord]:
    """Returns consent history for a candidate."""
    res = await db.execute(
        select(ConsentRecord)
        .where(
            ConsentRecord.candidate_id == candidate_id,
            ConsentRecord.organization_id == organization_id,
        )
        .order_by(desc(ConsentRecord.created_at))
    )
    return list(res.scalars().all())


async def list_consent_records(
    db: AsyncSession,
    organization_id: uuid.UUID,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[ConsentRecord], int]:
    """Lists organization consent records with optional status filter."""
    query = select(ConsentRecord).where(ConsentRecord.organization_id == organization_id)
    if status:
        query = query.where(ConsentRecord.status == status.upper())

    count_res = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_res.scalar_one()

    paginated_query = query.order_by(desc(ConsentRecord.created_at)).offset(offset).limit(limit)
    res = await db.execute(paginated_query)
    records = list(res.scalars().all())

    return records, total
