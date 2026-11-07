from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.repositories.organization_repository import OrganizationRepository
from app.schemas.organization import MembershipResponse, OrganizationResponse, UserOrganizationsResponse


class OrganizationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.org_repo = OrganizationRepository(db)

    async def get_user_organizations(self, user_id: uuid.UUID) -> UserOrganizationsResponse:
        memberships = await self.org_repo.get_user_memberships(user_id)
        return UserOrganizationsResponse(
            memberships=[
                MembershipResponse(
                    organization=OrganizationResponse.model_validate(m.organization),
                    role=m.role,
                    is_active=m.is_active,
                )
                for m in memberships
            ]
        )
