from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user, require_role
from app.db.session import get_db
from app.schemas.auth import CurrentUserResponse
from app.schemas.requisition import RequisitionListResponse, RequisitionResponse
from app.repositories.requisition_repository import RequisitionRepository

router = APIRouter(prefix="/requisitions", tags=["requisitions"])

_RECRUITER_OR_DELIVERY = require_role("recruiter", "delivery_head")


@router.get("", response_model=RequisitionListResponse)
async def list_requisitions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: CurrentUserResponse = _RECRUITER_OR_DELIVERY,
    db: AsyncSession = Depends(get_db),
) -> RequisitionListResponse:
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No organization membership found",
        )
    repo = RequisitionRepository(db)
    items, total = await repo.list_by_org(
        org_id=uuid.UUID(current_user.organization_id),
        page=page,
        page_size=page_size,
        status=status_filter,
    )
    return RequisitionListResponse(
        items=[RequisitionResponse.model_validate(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{requisition_id}", response_model=RequisitionResponse)
async def get_requisition(
    requisition_id: uuid.UUID,
    current_user: CurrentUserResponse = _RECRUITER_OR_DELIVERY,
    db: AsyncSession = Depends(get_db),
) -> RequisitionResponse:
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No organization membership found",
        )
    repo = RequisitionRepository(db)
    req = await repo.get_by_id_and_org(
        requisition_id=requisition_id,
        org_id=uuid.UUID(current_user.organization_id),
    )
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requisition not found")
    return RequisitionResponse.model_validate(req)
