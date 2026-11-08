from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidate import Candidate
from app.models.evaluation import Evaluation, EvaluationEvidence, RecruiterReview

logger = logging.getLogger("shortlistai.ranking")


class RankingService:
    """
    Deterministic candidate ranking and multi-attribute filtering service.
    Enforces that low-scoring candidates remain visible and searchable with
    zero automatic rejection thresholds.
    """

    async def list_ranked_evaluations(
        self,
        db: AsyncSession,
        requisition_id: uuid.UUID,
        organization_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "score_desc",
        score_min: Optional[float] = None,
        score_max: Optional[float] = None,
        confidence_level: Optional[str] = None,
        review_decision: Optional[str] = None,
        missing_evidence_only: bool = False,
        must_have_matched_only: bool = False,
        search: Optional[str] = None,
    ) -> Tuple[List[Evaluation], int]:
        """
        Retrieves paginated, ranked candidate evaluations for a requisition.
        """
        # Base query joining candidates and only considering current evaluations
        query = (
            select(Evaluation)
            .join(Candidate, Evaluation.candidate_id == Candidate.id)
            .where(
                and_(
                    Evaluation.requisition_id == requisition_id,
                    Evaluation.is_current == True,
                    or_(
                        Evaluation.organization_id == organization_id,
                        Evaluation.organization_id.is_(None),
                    ),
                    Candidate.organization_id == organization_id,
                )
            )
            .options(
                selectinload(Evaluation.candidate).selectinload(Candidate.skills),
                selectinload(Evaluation.candidate).selectinload(Candidate.employments),
                selectinload(Evaluation.evidence),
                selectinload(Evaluation.reviews),
            )
        )

        # Apply Filters
        if score_min is not None:
            query = query.where(Evaluation.normalized_score >= score_min)
        if score_max is not None:
            query = query.where(Evaluation.normalized_score <= score_max)
        if confidence_level:
            query = query.where(Evaluation.confidence_level == confidence_level.upper())

        if missing_evidence_only:
            query = query.where(Evaluation.evidence_coverage < 80.0)

        if search:
            s_term = f"%{search.strip().lower()}%"
            query = query.where(
                or_(
                    func.lower(Candidate.full_name).ilike(s_term),
                    func.lower(Candidate.email).ilike(s_term),
                )
            )

        # Count total before pagination
        count_stmt = select(func.count()).select_from(query.subquery())
        total_res = await db.execute(count_stmt)
        total = total_res.scalar_one()

        # Deterministic Sorting & Tie-breaking
        if sort_by == "score_asc":
            query = query.order_by(
                Evaluation.normalized_score.asc(),
                Candidate.created_at.asc(),
                Evaluation.id.asc(),
            )
        elif sort_by == "coverage_desc":
            query = query.order_by(
                Evaluation.evidence_coverage.desc(),
                Evaluation.normalized_score.desc(),
                Evaluation.id.asc(),
            )
        elif sort_by == "experience_desc":
            query = query.order_by(
                Candidate.total_experience_years.desc().nullslast(),
                Evaluation.normalized_score.desc(),
                Evaluation.id.asc(),
            )
        elif sort_by == "name_asc":
            query = query.order_by(
                Candidate.full_name.asc(),
                Evaluation.normalized_score.desc(),
            )
        else:
            # Default: score_desc with strict deterministic tie-breakers
            query = query.order_by(
                Evaluation.normalized_score.desc(),
                Evaluation.evidence_coverage.desc(),
                Candidate.created_at.asc(),
                Evaluation.id.asc(),
            )

        # Pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await db.execute(query)
        evaluations = list(result.scalars().all())

        # Post-filter for review_decision or must_have_matched_only if requested
        filtered_evals = []
        for ev in evaluations:
            # Review decision filter
            if review_decision:
                latest_review = ev.reviews[-1] if ev.reviews else None
                current_decision = latest_review.decision if latest_review else "UNREVIEWED"
                if current_decision.upper() != review_decision.upper():
                    continue

            # Must have matched filter
            if must_have_matched_only:
                all_mh_matched = True
                for item in ev.evidence or []:
                    # Check if criterion was must-have and not MATCHED
                    if "must_have" in (item.flags_json or {}).get("type", "") and item.evidence_status != "MATCHED":
                        all_mh_matched = False
                        break
                if not all_mh_matched:
                    continue

            filtered_evals.append(ev)

        return filtered_evals, total


ranking_service = RankingService()
