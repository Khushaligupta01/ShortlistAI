from __future__ import annotations

import math
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies.auth import get_current_user, require_role
from app.db.session import get_db
from app.models.candidate import Candidate
from app.models.evaluation import Evaluation, EvaluationEvidence, EvaluationRun, RecruiterReview
from app.models.organization import OrganizationMembership
from app.models.requisition import Requisition
from app.schemas.auth import CurrentUserResponse
from app.schemas.evaluation import (
    BatchEvaluationRequest,
    CriterionEvidenceResponse,
    EvaluationListResponse,
    EvaluationResponse,
    EvaluationRunResponse,
    RecruiterReviewRequest,
    RecruiterReviewResponse,
)
from app.services.evaluation_service import evaluation_service
from app.services.ranking_service import ranking_service

router = APIRouter(tags=["evaluations"])

_RECRUITER_ONLY = require_role("recruiter")
_RECRUITER_OR_DELIVERY = require_role("recruiter", "delivery_head")
_ANY_AUTHENTICATED = Depends(get_current_user)


def _require_org(user: CurrentUserResponse) -> uuid.UUID:
    if not user.organization_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No organization membership found")
    return uuid.UUID(user.organization_id)


def _mask_pii_email(email: Optional[str]) -> Optional[str]:
    if not email or "@" not in email:
        return email
    local, domain = email.split("@", 1)
    if len(local) <= 1:
        return f"*@{domain}"
    return f"{local[0]}***@{domain}"


from sqlalchemy.inspection import inspect


def _evaluation_to_response(ev: Evaluation, mask_pii: bool = False) -> EvaluationResponse:
    state = inspect(ev)
    cand = None
    if "candidate" not in state.unloaded:
        cand = ev.candidate

    cand_name = cand.full_name if cand else None
    cand_email = cand.email if cand else None
    if mask_pii and cand_email:
        cand_email = _mask_pii_email(cand_email)

    skills_list = []
    if cand:
        cand_state = inspect(cand)
        if "skills" not in cand_state.unloaded:
            skills_list = [s.raw_name for s in (cand.skills or [])]

    evidence_res = None
    if "evidence" not in state.unloaded and ev.evidence is not None:
        evidence_res = [
            CriterionEvidenceResponse(
                id=str(e.id),
                scorecard_criterion_id=str(e.scorecard_criterion_id),
                criterion_name=(e.criterion.criterion_name if ("criterion" not in inspect(e).unloaded and e.criterion) else None),
                criterion_type=(e.criterion.criterion_type if ("criterion" not in inspect(e).unloaded and e.criterion) else None),
                evidence_status=e.evidence_status,
                confidence_score=float(e.confidence_score),
                awarded_points=float(e.awarded_points),
                maximum_points=float(e.maximum_points),
                evidence_text=e.evidence_text,
                source_reference=e.source_reference,
                explanation=e.explanation,
                is_overridden=e.is_overridden,
                override_reason=e.override_reason,
                created_at=e.created_at,
            )
            for e in ev.evidence
        ]

    reviews_res = None
    latest_decision = "UNREVIEWED"
    if "reviews" not in state.unloaded and ev.reviews is not None:
        reviews_res = [
            RecruiterReviewResponse(
                id=str(r.id),
                evaluation_id=str(r.evaluation_id),
                recruiter_id=str(r.recruiter_id),
                decision=r.decision,
                notes=r.notes,
                reviewed_at=r.reviewed_at,
            )
            for r in ev.reviews
        ]
        if ev.reviews and len(ev.reviews) > 0:
            latest_decision = ev.reviews[-1].decision

    return EvaluationResponse(
        id=str(ev.id),
        candidate_id=str(ev.candidate_id),
        candidate_name=cand_name,
        candidate_email=cand_email,
        candidate_location=cand.location if cand else None,
        candidate_experience_years=float(cand.total_experience_years) if (cand and cand.total_experience_years is not None) else None,
        candidate_notice_days=cand.notice_period_days if cand else None,
        candidate_skills=skills_list,
        requisition_id=str(ev.requisition_id),
        scorecard_id=str(ev.scorecard_id),
        scorecard_version=ev.scorecard_version,
        version_number=ev.version_number,
        total_score=float(ev.total_score),
        raw_score=float(ev.raw_score),
        normalized_score=float(ev.normalized_score),
        evidence_coverage=float(ev.evidence_coverage),
        confidence_level=ev.confidence_level,
        evaluation_status=ev.evaluation_status,
        is_current=ev.is_current,
        score_breakdown=ev.score_breakdown_json or {},
        evidence=evidence_res,
        reviews=reviews_res,
        latest_review_decision=latest_decision,
        evaluated_at=ev.evaluated_at,
        created_at=ev.created_at,
    )


# -----------------------------------------------------------------------------
# 1. Start Batch Evaluation
# -----------------------------------------------------------------------------
@router.post(
    "/requisitions/{requisition_id}/evaluations",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=EvaluationRunResponse,
)
async def start_batch_evaluation(
    requisition_id: uuid.UUID,
    payload: Optional[BatchEvaluationRequest] = None,
    current_user: CurrentUserResponse = _RECRUITER_OR_DELIVERY,
    db: AsyncSession = Depends(get_db),
) -> EvaluationRunResponse:
    org_id = _require_org(current_user)

    # Verify requisition
    req_res = await db.execute(
        select(Requisition).where(
            and_(Requisition.id == requisition_id, Requisition.organization_id == org_id)
        )
    )
    req = req_res.scalars().first()
    if not req:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Requisition not found.")

    try:
        cand_ids = payload.candidate_ids if payload else None
        run = await evaluation_service.start_batch_evaluation(
            db=db,
            requisition_id=requisition_id,
            organization_id=org_id,
            user_id=uuid.UUID(current_user.id),
            candidate_ids=cand_ids,
        )
        return EvaluationRunResponse(
            id=str(run.id),
            requisition_id=str(run.requisition_id),
            total_candidates=run.total_candidates,
            completed_count=run.completed_count,
            failed_count=run.failed_count,
            status=run.status,
            started_at=run.started_at,
            completed_at=run.completed_at,
            error_summary=run.error_summary,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))


# -----------------------------------------------------------------------------
# 2. Evaluate Single Candidate
# -----------------------------------------------------------------------------
@router.post(
    "/requisitions/{requisition_id}/candidates/{candidate_id}/evaluate",
    status_code=status.HTTP_200_OK,
    response_model=EvaluationResponse,
)
async def evaluate_single_candidate(
    requisition_id: uuid.UUID,
    candidate_id: uuid.UUID,
    current_user: CurrentUserResponse = _RECRUITER_OR_DELIVERY,
    db: AsyncSession = Depends(get_db),
) -> EvaluationResponse:
    org_id = _require_org(current_user)

    # Verify requisition
    req_res = await db.execute(
        select(Requisition).where(
            and_(Requisition.id == requisition_id, Requisition.organization_id == org_id)
        )
    )
    req = req_res.scalars().first()
    if not req:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Requisition not found.")

    try:
        evaluation = await evaluation_service.evaluate_candidate(
            db=db,
            requisition_id=requisition_id,
            candidate_id=candidate_id,
            organization_id=org_id,
            user_id=uuid.UUID(current_user.id),
        )

        # Reload with relationships
        full_res = await db.execute(
            select(Evaluation)
            .where(Evaluation.id == evaluation.id)
            .options(
                selectinload(Evaluation.candidate).selectinload(Candidate.skills),
                selectinload(Evaluation.evidence).selectinload(EvaluationEvidence.criterion),
                selectinload(Evaluation.reviews),
            )
        )
        full_eval = full_res.scalars().first()
        return _evaluation_to_response(full_eval or evaluation)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))


# -----------------------------------------------------------------------------
# 3. List Evaluations for Requisition (Ranked & Filtered)
# -----------------------------------------------------------------------------
@router.get(
    "/requisitions/{requisition_id}/evaluations",
    response_model=EvaluationListResponse,
)
async def list_evaluations(
    requisition_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("score_desc"),
    score_min: Optional[float] = Query(None, ge=0.0, le=100.0),
    score_max: Optional[float] = Query(None, ge=0.0, le=100.0),
    confidence_level: Optional[str] = Query(None),
    review_decision: Optional[str] = Query(None),
    missing_evidence_only: bool = Query(False),
    must_have_matched_only: bool = Query(False),
    search: Optional[str] = Query(None),
    current_user: CurrentUserResponse = _ANY_AUTHENTICATED,
    db: AsyncSession = Depends(get_db),
) -> EvaluationListResponse:
    org_id = _require_org(current_user)

    # Verify requisition
    req_res = await db.execute(
        select(Requisition).where(
            and_(Requisition.id == requisition_id, Requisition.organization_id == org_id)
        )
    )
    req = req_res.scalars().first()
    if not req:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Requisition not found.")

    is_client = current_user.role == "client_hiring_manager"

    evals, total = await ranking_service.list_ranked_evaluations(
        db=db,
        requisition_id=requisition_id,
        organization_id=org_id,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        score_min=score_min,
        score_max=score_max,
        confidence_level=confidence_level,
        review_decision=review_decision,
        missing_evidence_only=missing_evidence_only,
        must_have_matched_only=must_have_matched_only,
        search=search,
    )

    items = [_evaluation_to_response(ev, mask_pii=is_client) for ev in evals]
    total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1

    return EvaluationListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# -----------------------------------------------------------------------------
# 4. Get Evaluation Run Progress
# -----------------------------------------------------------------------------
@router.get(
    "/requisitions/{requisition_id}/evaluation-runs/{run_id}",
    response_model=EvaluationRunResponse,
)
async def get_evaluation_run(
    requisition_id: uuid.UUID,
    run_id: uuid.UUID,
    current_user: CurrentUserResponse = _RECRUITER_OR_DELIVERY,
    db: AsyncSession = Depends(get_db),
) -> EvaluationRunResponse:
    org_id = _require_org(current_user)

    stmt = select(EvaluationRun).where(
        and_(
            EvaluationRun.id == run_id,
            EvaluationRun.requisition_id == requisition_id,
            EvaluationRun.organization_id == org_id,
        )
    )
    res = await db.execute(stmt)
    run = res.scalars().first()
    if not run:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evaluation run not found.")

    return EvaluationRunResponse(
        id=str(run.id),
        requisition_id=str(run.requisition_id),
        total_candidates=run.total_candidates,
        completed_count=run.completed_count,
        failed_count=run.failed_count,
        status=run.status,
        started_at=run.started_at,
        completed_at=run.completed_at,
        error_summary=run.error_summary,
    )


# -----------------------------------------------------------------------------
# 5. Get Detailed Evaluation
# -----------------------------------------------------------------------------
@router.get(
    "/evaluations/{evaluation_id}",
    response_model=EvaluationResponse,
)
async def get_evaluation(
    evaluation_id: uuid.UUID,
    current_user: CurrentUserResponse = _ANY_AUTHENTICATED,
    db: AsyncSession = Depends(get_db),
) -> EvaluationResponse:
    org_id = _require_org(current_user)

    stmt = (
        select(Evaluation)
        .where(
            and_(
                Evaluation.id == evaluation_id,
                or_(
                    Evaluation.organization_id == org_id,
                    Evaluation.organization_id.is_(None),
                ),
            )
        )
        .options(
            selectinload(Evaluation.candidate).selectinload(Candidate.skills),
            selectinload(Evaluation.evidence).selectinload(EvaluationEvidence.criterion),
            selectinload(Evaluation.reviews),
        )
    )
    res = await db.execute(stmt)
    ev = res.scalars().first()
    if not ev:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evaluation not found.")

    is_client = current_user.role == "client_hiring_manager"
    return _evaluation_to_response(ev, mask_pii=is_client)


# -----------------------------------------------------------------------------
# 6. Get Criterion-Level Evidence for Evaluation
# -----------------------------------------------------------------------------
@router.get(
    "/evaluations/{evaluation_id}/evidence",
    response_model=List[CriterionEvidenceResponse],
)
async def get_evaluation_evidence(
    evaluation_id: uuid.UUID,
    current_user: CurrentUserResponse = _RECRUITER_OR_DELIVERY,
    db: AsyncSession = Depends(get_db),
) -> List[CriterionEvidenceResponse]:
    org_id = _require_org(current_user)

    stmt = (
        select(EvaluationEvidence)
        .join(Evaluation, EvaluationEvidence.evaluation_id == Evaluation.id)
        .where(
            and_(
                Evaluation.id == evaluation_id,
                or_(
                    Evaluation.organization_id == org_id,
                    Evaluation.organization_id.is_(None),
                ),
            )
        )
        .options(selectinload(EvaluationEvidence.criterion))
    )
    res = await db.execute(stmt)
    items = list(res.scalars().all())
    if not items:
        # Check if evaluation exists
        ev_stmt = select(Evaluation).where(
            and_(
                Evaluation.id == evaluation_id,
                or_(
                    Evaluation.organization_id == org_id,
                    Evaluation.organization_id.is_(None),
                ),
            )
        )
        ev_res = await db.execute(ev_stmt)
        if not ev_res.scalars().first():
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Evaluation not found.")

    return [
        CriterionEvidenceResponse(
            id=str(e.id),
            scorecard_criterion_id=str(e.scorecard_criterion_id),
            criterion_name=e.criterion.criterion_name if e.criterion else None,
            criterion_type=e.criterion.criterion_type if e.criterion else None,
            evidence_status=e.evidence_status,
            confidence_score=float(e.confidence_score),
            awarded_points=float(e.awarded_points),
            maximum_points=float(e.maximum_points),
            evidence_text=e.evidence_text,
            source_reference=e.source_reference,
            explanation=e.explanation,
            is_overridden=e.is_overridden,
            override_reason=e.override_reason,
            created_at=e.created_at,
        )
        for e in items
    ]


# -----------------------------------------------------------------------------
# 7. Save Recruiter Review
# -----------------------------------------------------------------------------
@router.post(
    "/evaluations/{evaluation_id}/review",
    status_code=status.HTTP_200_OK,
    response_model=RecruiterReviewResponse,
)
async def save_recruiter_review(
    evaluation_id: uuid.UUID,
    payload: RecruiterReviewRequest,
    current_user: CurrentUserResponse = _RECRUITER_OR_DELIVERY,
    db: AsyncSession = Depends(get_db),
) -> RecruiterReviewResponse:
    org_id = _require_org(current_user)

    try:
        review = await evaluation_service.record_recruiter_review(
            db=db,
            evaluation_id=evaluation_id,
            recruiter_id=uuid.UUID(current_user.id),
            organization_id=org_id,
            decision=payload.decision,
            notes=payload.notes,
        )
        return RecruiterReviewResponse(
            id=str(review.id),
            evaluation_id=str(review.evaluation_id),
            recruiter_id=str(review.recruiter_id),
            decision=review.decision,
            notes=review.notes,
            reviewed_at=review.reviewed_at,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))


# -----------------------------------------------------------------------------
# 8. Recalculate Evaluation (Deterministic without re-calling LLM)
# -----------------------------------------------------------------------------
@router.post(
    "/evaluations/{evaluation_id}/recalculate",
    status_code=status.HTTP_200_OK,
    response_model=EvaluationResponse,
)
async def recalculate_evaluation(
    evaluation_id: uuid.UUID,
    current_user: CurrentUserResponse = _RECRUITER_OR_DELIVERY,
    db: AsyncSession = Depends(get_db),
) -> EvaluationResponse:
    org_id = _require_org(current_user)

    try:
        updated = await evaluation_service.recalculate_evaluation(
            db=db,
            evaluation_id=evaluation_id,
            organization_id=org_id,
        )
        full_res = await db.execute(
            select(Evaluation)
            .where(Evaluation.id == updated.id)
            .options(
                selectinload(Evaluation.candidate).selectinload(Candidate.skills),
                selectinload(Evaluation.evidence).selectinload(EvaluationEvidence.criterion),
                selectinload(Evaluation.reviews),
            )
        )
        full_eval = full_res.scalars().first()
        return _evaluation_to_response(full_eval or updated)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
