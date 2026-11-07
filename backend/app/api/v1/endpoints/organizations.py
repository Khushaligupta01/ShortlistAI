from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.db.session import get_db
from app.schemas.auth import CurrentUserResponse
from app.schemas.organization import UserOrganizationsResponse
from app.services.organization_service import OrganizationService

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("/me", response_model=UserOrganizationsResponse)
async def get_my_organizations(
    current_user: CurrentUserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserOrganizationsResponse:
    service = OrganizationService(db)
    return await service.get_user_organizations(uuid.UUID(current_user.id))
