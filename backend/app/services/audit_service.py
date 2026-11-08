from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.user import User

# Keys strictly excluded from audit payloads
SENSITIVE_KEYS = {
    "password", "password_hash", "hashed_password", "token", "access_token",
    "refresh_token", "jwt", "secret", "api_key", "raw_text", "normalized_text",
    "file_content", "authorization", "secret_key"
}


def sanitize_payload(payload: Any) -> Any:
    """Recursively removes sensitive keys and values from audit payload."""
    if not isinstance(payload, dict):
        return payload

    clean: Dict[str, Any] = {}
    for key, value in payload.items():
        lower_key = str(key).lower()
        if any(sens in lower_key for sens in SENSITIVE_KEYS):
            clean[key] = "[REDACTED]"
        elif isinstance(value, dict):
            clean[key] = sanitize_payload(value)
        elif isinstance(value, list):
            clean[key] = [sanitize_payload(item) if isinstance(item, dict) else item for item in value]
        else:
            clean[key] = value
    return clean


async def log_event(
    db: AsyncSession,
    organization_id: Optional[uuid.UUID],
    actor_user_id: Optional[uuid.UUID],
    event_type: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[uuid.UUID] = None,
    payload: Optional[Dict[str, Any]] = None,
    commit: bool = False,
) -> AuditLog:
    """Centralized immutable audit logger with automatic payload sanitization."""
    clean_payload = sanitize_payload(payload) if payload else None

    audit_entry = AuditLog(
        id=uuid.uuid4(),
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        payload_json=clean_payload,
        created_at=datetime.now(timezone.utc),
    )
    db.add(audit_entry)
    if commit:
        await db.commit()
        await db.refresh(audit_entry)
    else:
        await db.flush()

    return audit_entry


async def query_audit_logs(
    db: AsyncSession,
    organization_id: uuid.UUID,
    event_type: Optional[str] = None,
    resource_type: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 50,
) -> Tuple[List[Dict[str, Any]], int]:
    """Retrieves paginated audit events for an organization."""
    query = select(AuditLog).where(AuditLog.organization_id == organization_id)

    if event_type:
        query = query.where(AuditLog.event_type == event_type)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    if date_from:
        query = query.where(AuditLog.created_at >= date_from)
    if date_to:
        query = query.where(AuditLog.created_at <= date_to)

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Paginate
    offset = max(0, (page - 1) * page_size)
    paginated_query = query.order_by(desc(AuditLog.created_at)).offset(offset).limit(page_size)
    result = await db.execute(paginated_query)
    records = result.scalars().all()

    # Fetch actor names
    actor_ids = {r.actor_user_id for r in records if r.actor_user_id}
    actors_map: Dict[uuid.UUID, str] = {}
    if actor_ids:
        actors_result = await db.execute(select(User).where(User.id.in_(actor_ids)))
        for user in actors_result.scalars().all():
            actors_map[user.id] = getattr(user, "display_name", None) or getattr(user, "email", "User")

    formatted = []
    for r in records:
        formatted.append({
            "id": r.id,
            "organization_id": r.organization_id,
            "actor_user_id": r.actor_user_id,
            "actor_name": actors_map.get(r.actor_user_id) if r.actor_user_id else None,
            "event_type": r.event_type,
            "resource_type": r.resource_type,
            "resource_id": r.resource_id,
            "payload_json": r.payload_json,
            "created_at": r.created_at,
        })

    return formatted, total


async def get_audit_log_by_id(
    db: AsyncSession,
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
) -> Optional[Dict[str, Any]]:
    """Retrieves a single audit log event scoped to the organization."""
    query = select(AuditLog).where(
        AuditLog.id == event_id,
        AuditLog.organization_id == organization_id,
    )
    result = await db.execute(query)
    r = result.scalar_one_or_none()
    if not r:
        return None

    actor_name = None
    if r.actor_user_id:
        user_res = await db.execute(select(User).where(User.id == r.actor_user_id))
        user = user_res.scalar_one_or_none()
        if user:
            actor_name = getattr(user, "display_name", None) or getattr(user, "email", "User")

    return {
        "id": r.id,
        "organization_id": r.organization_id,
        "actor_user_id": r.actor_user_id,
        "actor_name": actor_name,
        "event_type": r.event_type,
        "resource_type": r.resource_type,
        "resource_id": r.resource_id,
        "payload_json": r.payload_json,
        "created_at": r.created_at,
    }
