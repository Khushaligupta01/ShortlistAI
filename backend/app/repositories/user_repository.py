from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User, RefreshToken
from app.core.security import hash_token


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.memberships))
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.memberships))
            .where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        email: str,
        password_hash: str,
        display_name: Optional[str] = None,
    ) -> User:
        user = User(
            email=email,
            password_hash=password_hash,
            display_name=display_name,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    # -----------------------------------------------------------------------
    # Refresh token operations
    # -----------------------------------------------------------------------

    async def store_refresh_token(
        self, user_id: uuid.UUID, token: str, expires_at: datetime
    ) -> RefreshToken:
        rt = RefreshToken(
            user_id=user_id,
            token_hash=hash_token(token),
            expires_at=expires_at,
        )
        self.db.add(rt)
        await self.db.flush()
        return rt

    async def get_valid_refresh_token(
        self, token: str
    ) -> Optional[RefreshToken]:
        hashed = hash_token(token)
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == hashed,
                RefreshToken.revoked.is_(False),
                RefreshToken.expires_at > datetime.now(timezone.utc),
            )
        )
        return result.scalar_one_or_none()

    async def revoke_refresh_token(self, token: str) -> bool:
        rt = await self.get_valid_refresh_token(token)
        if rt:
            rt.revoked = True
            await self.db.flush()
            return True
        return False

    async def revoke_all_user_refresh_tokens(self, user_id: uuid.UUID) -> None:
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked.is_(False),
            )
        )
        for rt in result.scalars().all():
            rt.revoked = True
        await self.db.flush()
