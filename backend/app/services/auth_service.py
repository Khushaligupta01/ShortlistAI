from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AuthenticationError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.models.organization import OrganizationMembership
from app.models.user import User
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import CurrentUserResponse, TokenResponse


# Generic error — never disclose which field was wrong
_AUTH_ERROR = "Invalid email or password"


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.user_repo = UserRepository(db)
        self.org_repo = OrganizationRepository(db)

    async def login(self, email: str, password: str) -> TokenResponse:
        user = await self.user_repo.get_by_email(email)

        # Uniform error for missing user OR wrong password
        if user is None or not verify_password(password, user.password_hash):
            raise AuthenticationError(_AUTH_ERROR)

        if not user.is_active:
            raise AuthenticationError(_AUTH_ERROR)

        # Pick the primary active membership for role/org in JWT
        primary = self._pick_primary_membership(user)
        role = primary.role if primary else "recruiter"
        org_id = str(primary.organization_id) if primary else None

        access_token = create_access_token(
            {
                "sub": str(user.id),
                "email": user.email,
                "role": role,
                "org_id": org_id,
            }
        )
        refresh_token = create_refresh_token(str(user.id))

        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        await self.user_repo.store_refresh_token(user.id, refresh_token, expires_at)
        await self.db.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def logout(self, refresh_token: str) -> None:
        await self.user_repo.revoke_refresh_token(refresh_token)
        await self.db.commit()

    async def refresh(self, refresh_token: str) -> TokenResponse:
        # Validate JWT structure first
        try:
            payload = decode_token(refresh_token)
        except JWTError:
            raise AuthenticationError("Invalid refresh token")

        if payload.get("type") != "refresh":
            raise AuthenticationError("Invalid token type")

        user_id_str = payload.get("sub")
        if not user_id_str:
            raise AuthenticationError("Invalid refresh token")

        # Check DB — must be stored and not revoked
        stored = await self.user_repo.get_valid_refresh_token(refresh_token)
        if not stored:
            raise AuthenticationError("Refresh token expired or revoked")

        # Revoke old token (single-use)
        stored.revoked = True

        user = await self.user_repo.get_by_id(uuid.UUID(user_id_str))
        if not user or not user.is_active:
            raise AuthenticationError("Account unavailable")

        primary = self._pick_primary_membership(user)
        role = primary.role if primary else "recruiter"
        org_id = str(primary.organization_id) if primary else None

        new_access = create_access_token(
            {"sub": str(user.id), "email": user.email, "role": role, "org_id": org_id}
        )
        new_refresh = create_refresh_token(str(user.id))
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        await self.user_repo.store_refresh_token(user.id, new_refresh, expires_at)
        await self.db.commit()

        return TokenResponse(access_token=new_access, refresh_token=new_refresh)

    async def get_current_user_info(self, user_id: str) -> CurrentUserResponse:
        user = await self.user_repo.get_by_id(uuid.UUID(user_id))
        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive")

        primary = self._pick_primary_membership(user)
        role = primary.role if primary else "recruiter"
        org_id = str(primary.organization_id) if primary else None

        return CurrentUserResponse(
            id=str(user.id),
            email=user.email,
            display_name=user.display_name,
            role=role,
            organization_id=org_id,
            is_active=user.is_active,
        )

    @staticmethod
    def _pick_primary_membership(
        user: User,
    ) -> Optional[OrganizationMembership]:
        active = [m for m in user.memberships if m.is_active]
        if not active:
            return None
        return sorted(active, key=lambda m: m.created_at)[0]
