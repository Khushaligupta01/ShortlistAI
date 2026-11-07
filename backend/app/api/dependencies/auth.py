from __future__ import annotations

import uuid
from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import decode_token
from app.db.session import get_db
from app.repositories.user_repository import UserRepository
from app.schemas.auth import CurrentUserResponse

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> CurrentUserResponse:
    """Extract and validate the JWT from the Authorization header."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    repo = UserRepository(db)
    user = await repo.get_by_id(uuid.UUID(user_id))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    role = payload.get("role", "recruiter")
    org_id = payload.get("org_id")

    return CurrentUserResponse(
        id=user_id,
        email=user.email,
        display_name=user.display_name,
        role=role,
        organization_id=org_id,
        is_active=user.is_active,
    )


def require_role(*allowed_roles: str) -> Callable:
    """Dependency factory: ensures the current user has one of the allowed roles."""

    async def checker(
        current_user: CurrentUserResponse = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> CurrentUserResponse:
        if current_user.role not in allowed_roles:
            # Write audit log for unauthorized attempt (best-effort, no crash if it fails)
            try:
                from app.models.audit import AuditLog
                log = AuditLog(
                    actor_user_id=uuid.UUID(current_user.id),
                    organization_id=uuid.UUID(current_user.organization_id)
                    if current_user.organization_id else None,
                    event_type="UNAUTHORIZED_ACCESS_ATTEMPT",
                    resource_type="endpoint",
                    payload_json={"role": current_user.role, "required_roles": list(allowed_roles)},
                )
                db.add(log)
                await db.commit()
            except Exception:
                pass

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return Depends(checker)
