from __future__ import annotations

import math
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.db.session import get_db
from app.repositories.user_repository import UserRepository
from app.schemas.auth import CurrentUserResponse
from app.schemas.candidate import (
    CandidateDetailResponse,
    CandidateEvaluationHistoryItemResponse,
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
    min_experience: Optional[float] = Query(None, ge=0),
    max_experience: Optional[float] = Query(None, ge=0),
    max_notice_days: Optional[int] = Query(None, ge=0),
    evaluation_status: Optional[str] = Query(None),
    review_decision: Optional[str] = Query(None),
    min_score: Optional[float] = Query(None, ge=0, le=100),
    max_score: Optional[float] = Query(None, ge=0, le=100),
    sort_by: Optional[str] = Query("created_at"),
    sort_order: Optional[str] = Query("desc"),
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
        min_experience=min_experience,
        max_experience=max_experience,
        max_notice_days=max_notice_days,
        evaluation_status=evaluation_status,
        review_decision=review_decision,
        min_score=min_score,
        max_score=max_score,
        sort_by=sort_by,
        sort_order=sort_order,
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


@router.get(
    "/{candidate_id}/evaluations",
    response_model=List[CandidateEvaluationHistoryItemResponse],
)
async def get_candidate_evaluation_history(
    candidate_id: uuid.UUID,
    current_user: CurrentUserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[CandidateEvaluationHistoryItemResponse]:
    if not current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organization context.")

    org_id = uuid.UUID(current_user.organization_id)
    return await candidate_service.get_candidate_evaluation_history(
        db=db, candidate_id=candidate_id, organization_id=org_id
    )
