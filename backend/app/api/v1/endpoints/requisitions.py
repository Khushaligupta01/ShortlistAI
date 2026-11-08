from __future__ import annotations

import time
import uuid
from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.provider import LLMExtractionError, LLMProviderUnavailableError
from app.api.dependencies.auth import get_current_user, require_role
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.db.session import get_db
from app.schemas.auth import CurrentUserResponse
from app.schemas.candidate import (
    CandidateListItemResponse,
    CandidateListResponse,
)
from app.schemas.requisition import (
    ExtractRequirementsRequest,
    RequisitionCreate,
    RequisitionListResponse,
    RequisitionResponse,
    RequisitionSummaryResponse,
    ScorecardCreate,
    ScorecardResponse,
    ScorecardUpdate,
)
from app.services.candidate_service import candidate_service
from app.services.requisition_service import RequisitionService
from app.services.scorecard_service import ScorecardService
from app.repositories.user_repository import UserRepository
from app.models.resume import Resume
from app.models.evaluation import Evaluation, RecruiterReview
from app.models.scorecard import Scorecard
from sqlalchemy import distinct, func, select

router = APIRouter(prefix="/requisitions", tags=["requisitions"])

_RECRUITER_ONLY = require_role("recruiter")
_RECRUITER_OR_DELIVERY = require_role("recruiter", "delivery_head")

_EXTRACTION_RATE_LIMIT_WINDOW = 60  # seconds
_EXTRACTION_MAX_REQUESTS = 10
_extraction_call_times: dict[str, list[float]] = defaultdict(list)


def _check_extraction_rate_limit(key: str) -> None:
    now = time.time()
    times = [t for t in _extraction_call_times[key] if now - t < _EXTRACTION_RATE_LIMIT_WINDOW]
    if len(times) >= _EXTRACTION_MAX_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded for AI requirement extraction. Please wait before trying again.",
        )
    times.append(now)
    _extraction_call_times[key] = times


def _require_org(user: CurrentUserResponse) -> uuid.UUID:
    if not user.organization_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No organization membership found")
    return uuid.UUID(user.organization_id)


# ── Requisition CRUD ─────────────────────────────────────────────────────────

@router.get("", response_model=RequisitionListResponse)
async def list_requisitions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None, max_length=200),
    current_user: CurrentUserResponse = _RECRUITER_OR_DELIVERY,
    db: AsyncSession = Depends(get_db),
) -> RequisitionListResponse:
    org_id = _require_org(current_user)
    service = RequisitionService(db)
    items, total = await service.list(
        org_id=org_id, page=page, page_size=page_size,
        status=status_filter, search=search,
    )
    return RequisitionListResponse(
        items=[RequisitionResponse.model_validate(r) for r in items],
        total=total, page=page, page_size=page_size,
    )


@router.post("", response_model=RequisitionResponse, status_code=status.HTTP_201_CREATED)
async def create_requisition(
    body: RequisitionCreate,
    current_user: CurrentUserResponse = _RECRUITER_ONLY,
    db: AsyncSession = Depends(get_db),
) -> RequisitionResponse:
    org_id = _require_org(current_user)
    service = RequisitionService(db)
    req = await service.create(body, org_id, uuid.UUID(current_user.id))
    return RequisitionResponse.model_validate(req)


@router.get("/{requisition_id}", response_model=RequisitionResponse)
async def get_requisition(
    requisition_id: uuid.UUID,
    current_user: CurrentUserResponse = _RECRUITER_OR_DELIVERY,
    db: AsyncSession = Depends(get_db),
) -> RequisitionResponse:
    org_id = _require_org(current_user)
    service = RequisitionService(db)
    try:
        req = await service.get(requisition_id, org_id)
    except NotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    return RequisitionResponse.model_validate(req)


# ── AI extraction ────────────────────────────────────────────────────────────

@router.post("/extract-requirements")
async def extract_requirements(
    body: ExtractRequirementsRequest,
    current_user: CurrentUserResponse = _RECRUITER_ONLY,
    db: AsyncSession = Depends(get_db),
) -> dict:
    org_id = _require_org(current_user)
    _check_extraction_rate_limit(f"user:{current_user.id}")
    service = ScorecardService(db)
    try:
        result = await service.extract_requirements(
            jd_text=body.job_description,
            org_id=org_id,
            user_id=uuid.UUID(current_user.id),
        )
    except LLMProviderUnavailableError as e:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except LLMExtractionError as e:
        err_msg = str(e)
        if "quota" in err_msg.lower() or "credit" in err_msg.lower():
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                detail="AI provider quota exhausted. Check your provider billing or configure scorecard criteria manually.",
            )
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail=f"AI extraction failed: {err_msg}",
        )
    return result.model_dump()


# ── Scorecard endpoints ──────────────────────────────────────────────────────

@router.post(
    "/{requisition_id}/scorecards",
    response_model=ScorecardResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_scorecard(
    requisition_id: uuid.UUID,
    body: ScorecardCreate,
    current_user: CurrentUserResponse = _RECRUITER_ONLY,
    db: AsyncSession = Depends(get_db),
) -> ScorecardResponse:
    org_id = _require_org(current_user)
    service = ScorecardService(db)
    try:
        sc = await service.create(
            requisition_id, body, org_id, uuid.UUID(current_user.id)
        )
    except NotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except ConflictError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    except ValidationError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))
    return ScorecardResponse.model_validate(sc)


@router.get("/{requisition_id}/scorecard", response_model=ScorecardResponse)
async def get_scorecard(
    requisition_id: uuid.UUID,
    current_user: CurrentUserResponse = _RECRUITER_OR_DELIVERY,
    db: AsyncSession = Depends(get_db),
) -> ScorecardResponse:
    org_id = _require_org(current_user)
    service = ScorecardService(db)
    try:
        sc = await service.get(requisition_id, org_id)
    except NotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    return ScorecardResponse.model_validate(sc)


@router.put("/{requisition_id}/scorecard", response_model=ScorecardResponse)
async def update_scorecard(
    requisition_id: uuid.UUID,
    body: ScorecardUpdate,
    current_user: CurrentUserResponse = _RECRUITER_ONLY,
    db: AsyncSession = Depends(get_db),
) -> ScorecardResponse:
    org_id = _require_org(current_user)
    service = ScorecardService(db)
    try:
        sc = await service.update(
            requisition_id, body, org_id, uuid.UUID(current_user.id)
        )
    except NotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except ConflictError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    except ValidationError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))
    return ScorecardResponse.model_validate(sc)


@router.post(
    "/{requisition_id}/scorecard/approve",
    response_model=ScorecardResponse,
)
async def approve_scorecard(
    requisition_id: uuid.UUID,
    current_user: CurrentUserResponse = _RECRUITER_ONLY,
    db: AsyncSession = Depends(get_db),
) -> ScorecardResponse:
    org_id = _require_org(current_user)
    service = ScorecardService(db)
    try:
        sc = await service.approve(
            requisition_id, org_id, uuid.UUID(current_user.id)
        )
    except NotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except ConflictError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    except ValidationError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))
    return ScorecardResponse.model_validate(sc)


@router.post(
    "/{requisition_id}/scorecard/duplicate",
    response_model=ScorecardResponse,
    status_code=status.HTTP_201_CREATED,
)
async def duplicate_scorecard(
    requisition_id: uuid.UUID,
    current_user: CurrentUserResponse = _RECRUITER_ONLY,
    db: AsyncSession = Depends(get_db),
) -> ScorecardResponse:
    org_id = _require_org(current_user)
    service = ScorecardService(db)
    try:
        sc = await service.duplicate(
            requisition_id, org_id, uuid.UUID(current_user.id)
        )
    except NotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except ConflictError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    return ScorecardResponse.model_validate(sc)


# ── Requisition Candidates & Summary ─────────────────────────────────────────

@router.get("/{requisition_id}/summary", response_model=RequisitionSummaryResponse)
async def get_requisition_summary(
    requisition_id: uuid.UUID,
    current_user: CurrentUserResponse = _RECRUITER_OR_DELIVERY,
    db: AsyncSession = Depends(get_db),
) -> RequisitionSummaryResponse:
    org_id = _require_org(current_user)
    service = RequisitionService(db)
    try:
        req = await service.get(requisition_id, org_id)
    except NotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))

    # Candidate count
    cand_stmt = select(func.count(distinct(Resume.candidate_id))).where(
        Resume.requisition_id == requisition_id,
        Resume.candidate_id.is_not(None),
    )
    candidate_count = (await db.execute(cand_stmt)).scalar() or 0

    # Evaluated count & score metrics
    eval_stmt = select(
        func.count(Evaluation.id),
        func.avg(Evaluation.total_score),
        func.max(Evaluation.total_score),
    ).where(
        Evaluation.requisition_id == requisition_id,
        Evaluation.is_current == True,
        Evaluation.evaluation_status == "COMPLETED",
    )
    eval_res = (await db.execute(eval_stmt)).first()
    evaluated_count = eval_res[0] if eval_res and eval_res[0] else 0
    avg_score = round(float(eval_res[1]), 1) if eval_res and eval_res[1] is not None else None
    top_score = round(float(eval_res[2]), 1) if eval_res and eval_res[2] is not None else None

    # Review metrics
    reviewed_eval_sub = select(RecruiterReview.evaluation_id).where(
        RecruiterReview.organization_id == org_id,
        RecruiterReview.decision != "UNREVIEWED",
    )
    pending_stmt = select(func.count(distinct(Evaluation.candidate_id))).where(
        Evaluation.requisition_id == requisition_id,
        Evaluation.is_current == True,
        Evaluation.evaluation_status == "COMPLETED",
        ~Evaluation.id.in_(reviewed_eval_sub),
    )
    pending_reviews_count = (await db.execute(pending_stmt)).scalar() or 0

    # Shortlisted, rejected, hold
    async def _count_decision(decision_val: str) -> int:
        stmt = (
            select(func.count(distinct(Evaluation.candidate_id)))
            .join(RecruiterReview, RecruiterReview.evaluation_id == Evaluation.id)
            .where(
                Evaluation.requisition_id == requisition_id,
                Evaluation.is_current == True,
                RecruiterReview.decision == decision_val,
            )
        )
        return (await db.execute(stmt)).scalar() or 0

    shortlisted_count = await _count_decision("SHORTLIST")
    rejected_count = await _count_decision("REJECT")
    hold_count = await _count_decision("HOLD")

    # Scorecard version & id
    sc_stmt = (
        select(Scorecard)
        .where(Scorecard.requisition_id == requisition_id, Scorecard.status == "approved")
        .order_by(Scorecard.version_number.desc())
    )
    sc_res = await db.execute(sc_stmt)
    sc = sc_res.scalars().first()

    return RequisitionSummaryResponse(
        id=req.id,
        title=req.title,
        status=req.status,
        location=req.location,
        created_at=req.created_at,
        candidate_count=candidate_count,
        evaluated_count=evaluated_count,
        pending_reviews_count=pending_reviews_count,
        shortlisted_count=shortlisted_count,
        rejected_count=rejected_count,
        hold_count=hold_count,
        average_score=avg_score,
        top_score=top_score,
        approved_scorecard_id=sc.id if sc else None,
        scorecard_version=sc.version_number if sc else None,
    )


@router.get("/{requisition_id}/candidates", response_model=CandidateListResponse)
async def list_requisition_candidates(
    requisition_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: Optional[str] = Query(None, max_length=200),
    skill: Optional[str] = Query(None, max_length=100),
    location: Optional[str] = Query(None, max_length=100),
    min_experience: Optional[float] = Query(None, ge=0),
    max_experience: Optional[float] = Query(None, ge=0),
    max_notice_days: Optional[int] = Query(None, ge=0),
    evaluation_status: Optional[str] = Query(None),
    review_decision: Optional[str] = Query(None),
    min_score: Optional[float] = Query(None, ge=0, le=100),
    max_score: Optional[float] = Query(None, ge=0, le=100),
    sort_by: Optional[str] = Query("score"),
    sort_order: Optional[str] = Query("desc"),
    current_user: CurrentUserResponse = _RECRUITER_OR_DELIVERY,
    db: AsyncSession = Depends(get_db),
) -> CandidateListResponse:
    org_id = _require_org(current_user)
    repo = UserRepository(db)
    user = await repo.get_by_id(uuid.UUID(current_user.id))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")

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

    import math
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    return CandidateListResponse(
        items=[CandidateListItemResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )

