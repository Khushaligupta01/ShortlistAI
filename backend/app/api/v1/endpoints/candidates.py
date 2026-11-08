from __future__ import annotations

import math
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.db.session import get_db
from app.repositories.user_repository import UserRepository
from app.schemas.auth import CurrentUserResponse
from app.schemas.candidate import (
    CandidateDetailResponse,
    CandidateListItemResponse,
    CandidateListResponse,
)
from app.services.candidate_service import candidate_service

router = APIRouter(prefix="/candidates", tags=["candidates"])


async def _get_db_user(current_user: CurrentUserResponse, db: AsyncSession):
    repo = UserRepository(db)
    user = await repo.get_by_id(uuid.UUID(current_user.id))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    return user


@router.get("", response_model=CandidateListResponse)
async def list_candidates(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: Optional[str] = Query(None, max_length=200),
    requisition_id: Optional[uuid.UUID] = Query(None),
    skill: Optional[str] = Query(None, max_length=100),
    location: Optional[str] = Query(None, max_length=100),
    current_user: CurrentUserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CandidateListResponse:
    if not current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organization context.")

    org_id = uuid.UUID(current_user.organization_id)
    user = await _get_db_user(current_user, db)

    items, total = await candidate_service.list_candidates(
        db=db,
        user=user,
        organization_id=org_id,
        page=page,
        page_size=page_size,
        search=search,
        requisition_id=requisition_id,
        skill=skill,
        location=location,
    )

    total_pages = math.ceil(total / page_size) if total > 0 else 1
    return CandidateListResponse(
        items=[CandidateListItemResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{candidate_id}", response_model=CandidateDetailResponse)
async def get_candidate_details(
    candidate_id: uuid.UUID,
    current_user: CurrentUserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CandidateDetailResponse:
    user = await _get_db_user(current_user, db)
    candidate = await candidate_service.get_candidate(
        db=db, candidate_id=candidate_id, user=user
    )
    return CandidateDetailResponse.model_validate(candidate)
