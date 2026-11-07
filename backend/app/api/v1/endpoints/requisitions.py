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
from app.schemas.requisition import (
    ExtractRequirementsRequest,
    RequisitionCreate,
    RequisitionListResponse,
    RequisitionResponse,
    ScorecardCreate,
    ScorecardResponse,
    ScorecardUpdate,
)
from app.services.requisition_service import RequisitionService
from app.services.scorecard_service import ScorecardService

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
