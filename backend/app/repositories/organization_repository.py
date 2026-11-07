from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.organization import Organization, OrganizationMembership


class OrganizationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, org_id: uuid.UUID) -> Optional[Organization]:
        result = await self.db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[Organization]:
        result = await self.db.execute(
            select(Organization).where(Organization.name == name)
        )
        return result.scalar_one_or_none()

    async def create(self, name: str, org_type: str) -> Organization:
        org = Organization(name=name, org_type=org_type)
        self.db.add(org)
        await self.db.flush()
        await self.db.refresh(org)
        return org

    async def get_user_memberships(
        self, user_id: uuid.UUID
    ) -> List[OrganizationMembership]:
        result = await self.db.execute(
            select(OrganizationMembership)
            .options(selectinload(OrganizationMembership.organization))
            .where(
                OrganizationMembership.user_id == user_id,
                OrganizationMembership.is_active.is_(True),
            )
        )
        return list(result.scalars().all())

    async def add_member(
        self,
        user_id: uuid.UUID,
        org_id: uuid.UUID,
        role: str,
    ) -> OrganizationMembership:
        membership = OrganizationMembership(
            user_id=user_id,
            organization_id=org_id,
            role=role,
        )
        self.db.add(membership)
        await self.db.flush()
        return membership

    async def get_membership(
        self, user_id: uuid.UUID, org_id: uuid.UUID
    ) -> Optional[OrganizationMembership]:
        result = await self.db.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user_id,
                OrganizationMembership.organization_id == org_id,
                OrganizationMembership.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()
