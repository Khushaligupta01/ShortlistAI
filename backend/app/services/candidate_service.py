from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidate import Candidate
from app.models.evaluation import Evaluation, RecruiterReview
from app.models.organization import OrganizationMembership
from app.models.user import User
from app.repositories.candidate_repository import candidate_repository
from app.schemas.candidate import CandidateEvaluationHistoryItemResponse


class CandidateService:
    """Business logic for candidate profiles, privacy masking, and querying."""

    async def _get_user_role(
        self, db: AsyncSession, user: User, organization_id: uuid.UUID
    ) -> str:
        q = select(OrganizationMembership).where(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.is_active == True,
        )
        res = await db.execute(q)
        m = res.scalars().first()
        if not m:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not belong to this organization.",
            )
        return m.role

    @staticmethod
    def _mask_candidate_if_needed(candidate: Any, role: str) -> None:
        """Mask PII (email, phone) for client users per privacy requirements."""
        if role.startswith("client"):
            if isinstance(candidate, dict):
                candidate["email"] = "[Contact Protected]"
                candidate["phone"] = "[Contact Protected]"
            else:
                candidate.email = "[Contact Protected]"
                candidate.phone = "[Contact Protected]"

    async def list_candidates(
        self,
        db: AsyncSession,
        user: User,
        organization_id: uuid.UUID,
        page: int = 1,
        page_size: int = 25,
        search: Optional[str] = None,
        requisition_id: Optional[uuid.UUID] = None,
        skill: Optional[str] = None,
        location: Optional[str] = None,
        min_experience: Optional[float] = None,
        max_experience: Optional[float] = None,
        max_notice_days: Optional[int] = None,
        evaluation_status: Optional[str] = None,
        review_decision: Optional[str] = None,
        min_score: Optional[float] = None,
        max_score: Optional[float] = None,
        sort_by: Optional[str] = "created_at",
        sort_order: Optional[str] = "desc",
    ) -> Tuple[List[Dict[str, Any]], int]:
        role = await self._get_user_role(db, user, organization_id)

        items, total = await candidate_repository.list_candidates(
            db=db,
            organization_id=organization_id,
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

        for c in items:
            self._mask_candidate_if_needed(c, role)

        return items, total

    async def get_candidate(
        self, db: AsyncSession, candidate_id: uuid.UUID, user: User
    ) -> Candidate:
        candidate = await candidate_repository.get_candidate_by_id(db, candidate_id)
        if not candidate:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found.")

        role = await self._get_user_role(db, user, candidate.organization_id)
        self._mask_candidate_if_needed(candidate, role)
        return candidate

    async def get_candidate_evaluation_history(
        self,
        db: AsyncSession,
        candidate_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> List[CandidateEvaluationHistoryItemResponse]:
        stmt = (
            select(Evaluation)
            .options(
                selectinload(Evaluation.requisition),
                selectinload(Evaluation.reviews),
            )
            .where(
                Evaluation.candidate_id == candidate_id,
                Evaluation.organization_id == organization_id,
            )
            .order_by(Evaluation.version_number.desc(), Evaluation.created_at.desc())
        )
        res = await db.execute(stmt)
        evals = res.scalars().all()

        items: List[CandidateEvaluationHistoryItemResponse] = []
        for ev in evals:
            latest_rev = (
                sorted(ev.reviews, key=lambda r: r.reviewed_at, reverse=True)[0]
                if ev.reviews
                else None
            )
            breakdown = ev.score_breakdown_json or {}
            items.append(
                CandidateEvaluationHistoryItemResponse(
                    id=str(ev.id),
                    requisition_id=str(ev.requisition_id),
                    requisition_title=ev.requisition.title if ev.requisition else None,
                    scorecard_id=str(ev.scorecard_id),
                    scorecard_version=ev.scorecard_version,
                    overall_score=float(ev.total_score),
                    confidence_score=float(breakdown.get("confidence_score", 0.9)),
                    evidence_coverage=float(ev.evidence_coverage),
                    evaluation_status=ev.evaluation_status,
                    is_current=ev.is_current,
                    summary=breakdown.get("summary"),
                    strengths=breakdown.get("strengths", []),
                    gaps=breakdown.get("gaps", []),
                    risks=breakdown.get("risks", []),
                    review_decision=latest_rev.decision if latest_rev else None,
                    review_notes=latest_rev.notes if latest_rev else None,
                    reviewed_at=latest_rev.reviewed_at if latest_rev else None,
                    created_at=ev.created_at,
                )
            )
        return items


candidate_service = CandidateService()
