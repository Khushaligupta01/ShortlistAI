from __future__ import annotations

import uuid
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy import distinct, func, select, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.requisition import Requisition
from app.models.candidate import Candidate
from app.models.resume import Resume, UploadBatch
from app.models.evaluation import Evaluation, RecruiterReview
from app.models.candidate_note import CandidateNote
from app.models.user import User
from app.schemas.dashboard import (
    DashboardMetricsResponse,
    RequisitionOverviewItem,
    ProcessingOverviewResponse,
    DashboardActivityItem,
    DashboardActivityResponse,
    RecruiterDashboardResponse,
)


def _ensure_utc(dt: datetime | None) -> datetime:
    if dt is None:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class DashboardService:
    async def get_dashboard_metrics(
        self, db: AsyncSession, organization_id: uuid.UUID
    ) -> DashboardMetricsResponse:
        # 1. Active requisitions
        active_reqs_stmt = select(func.count(Requisition.id)).where(
            Requisition.organization_id == organization_id,
            Requisition.status == "active",
        )
        active_reqs = (await db.execute(active_reqs_stmt)).scalar() or 0

        # 2. Total candidates
        total_candidates_stmt = select(func.count(Candidate.id)).where(
            Candidate.organization_id == organization_id
        )
        total_candidates = (await db.execute(total_candidates_stmt)).scalar() or 0

        # 3. Resumes processed
        processed_resumes_stmt = select(func.count(Resume.id)).where(
            Resume.organization_id == organization_id,
            Resume.parse_status == "parsed",
        )
        resumes_processed = (await db.execute(processed_resumes_stmt)).scalar() or 0

        # 4. Resumes pending
        pending_resumes_stmt = select(func.count(Resume.id)).where(
            Resume.organization_id == organization_id,
            Resume.parse_status.in_(["pending", "processing"]),
        )
        resumes_pending = (await db.execute(pending_resumes_stmt)).scalar() or 0

        # 5. Failed resume jobs
        failed_jobs_stmt = select(func.count(Resume.id)).where(
            Resume.organization_id == organization_id,
            Resume.parse_status == "failed",
        )
        failed_jobs = (await db.execute(failed_jobs_stmt)).scalar() or 0

        # 6. Completed evaluations
        completed_evals_stmt = select(func.count(Evaluation.id)).where(
            Evaluation.organization_id == organization_id,
            Evaluation.is_current == True,
            Evaluation.evaluation_status == "COMPLETED",
        )
        completed_evaluations = (await db.execute(completed_evals_stmt)).scalar() or 0

        # 7. Candidates awaiting review:
        # Completed current evaluations that don't have a non-UNREVIEWED decision
        reviewed_eval_ids_subquery = (
            select(RecruiterReview.evaluation_id)
            .where(
                RecruiterReview.organization_id == organization_id,
                RecruiterReview.decision != "UNREVIEWED",
            )
        )
        awaiting_review_stmt = select(func.count(distinct(Evaluation.candidate_id))).where(
            Evaluation.organization_id == organization_id,
            Evaluation.is_current == True,
            Evaluation.evaluation_status == "COMPLETED",
            ~Evaluation.id.in_(reviewed_eval_ids_subquery),
        )
        candidates_awaiting_review = (await db.execute(awaiting_review_stmt)).scalar() or 0

        # 8. Candidates shortlisted:
        # Candidates whose latest current evaluation review decision is in ('SHORTLIST', 'INTERNALLY_SHORTLISTED')
        shortlisted_stmt = (
            select(func.count(distinct(Evaluation.candidate_id)))
            .join(RecruiterReview, RecruiterReview.evaluation_id == Evaluation.id)
            .where(
                Evaluation.organization_id == organization_id,
                Evaluation.is_current == True,
                RecruiterReview.decision.in_(["SHORTLIST", "INTERNALLY_SHORTLISTED"]),
            )
        )
        candidates_shortlisted = (await db.execute(shortlisted_stmt)).scalar() or 0

        return DashboardMetricsResponse(
            active_requisitions=active_reqs,
            total_candidates=total_candidates,
            resumes_processed=resumes_processed,
            resumes_pending=resumes_pending,
            failed_jobs=failed_jobs,
            candidates_awaiting_review=candidates_awaiting_review,
            candidates_shortlisted=candidates_shortlisted,
            completed_evaluations=completed_evaluations,
        )

    async def get_requisition_overview(
        self, db: AsyncSession, organization_id: uuid.UUID, limit: int = 15
    ) -> List[RequisitionOverviewItem]:
        stmt = (
            select(Requisition)
            .where(Requisition.organization_id == organization_id)
            .order_by(Requisition.created_at.desc())
            .limit(limit)
        )
        reqs = (await db.execute(stmt)).scalars().all()

        items: List[RequisitionOverviewItem] = []
        for r in reqs:
            # Candidate count associated with this requisition
            c_stmt = select(func.count(distinct(Resume.candidate_id))).where(
                Resume.requisition_id == r.id,
                Resume.candidate_id.is_not(None),
            )
            candidate_count = (await db.execute(c_stmt)).scalar() or 0

            # Evaluation metrics
            eval_stmt = select(
                func.count(Evaluation.id),
                func.avg(Evaluation.total_score),
                func.max(Evaluation.total_score),
            ).where(
                Evaluation.requisition_id == r.id,
                Evaluation.is_current == True,
                Evaluation.evaluation_status == "COMPLETED",
            )
            eval_res = (await db.execute(eval_stmt)).first()
            evaluated_count = eval_res[0] if eval_res and eval_res[0] else 0
            avg_score = round(float(eval_res[1]), 1) if eval_res and eval_res[1] is not None else None
            top_score = round(float(eval_res[2]), 1) if eval_res and eval_res[2] is not None else None

            # Pending reviews
            rev_sub = select(RecruiterReview.evaluation_id).where(
                RecruiterReview.organization_id == organization_id,
                RecruiterReview.decision != "UNREVIEWED",
            )
            pending_stmt = select(func.count(distinct(Evaluation.candidate_id))).where(
                Evaluation.requisition_id == r.id,
                Evaluation.is_current == True,
                Evaluation.evaluation_status == "COMPLETED",
                ~Evaluation.id.in_(rev_sub),
            )
            pending_reviews = (await db.execute(pending_stmt)).scalar() or 0

            # Shortlisted
            shortlisted_stmt = (
                select(func.count(distinct(Evaluation.candidate_id)))
                .join(RecruiterReview, RecruiterReview.evaluation_id == Evaluation.id)
                .where(
                    Evaluation.requisition_id == r.id,
                    Evaluation.is_current == True,
                    RecruiterReview.decision.in_(["SHORTLIST", "INTERNALLY_SHORTLISTED"]),
                )
            )
            shortlisted = (await db.execute(shortlisted_stmt)).scalar() or 0

            items.append(
                RequisitionOverviewItem(
                    id=str(r.id),
                    title=r.title,
                    department=None,
                    location=r.location,
                    status=r.status,
                    target_hire_date=None,
                    candidate_count=candidate_count,
                    evaluated_count=evaluated_count,
                    pending_reviews_count=pending_reviews,
                    shortlisted_count=shortlisted,
                    average_score=avg_score,
                    top_score=top_score,
                    created_at=r.created_at,
                )
            )
        return items

    async def get_processing_overview(
        self, db: AsyncSession, organization_id: uuid.UUID
    ) -> ProcessingOverviewResponse:
        total_stmt = select(func.count(Resume.id)).where(Resume.organization_id == organization_id)
        total_uploaded = (await db.execute(total_stmt)).scalar() or 0

        parsed_stmt = select(func.count(Resume.id)).where(
            Resume.organization_id == organization_id,
            Resume.parse_status == "parsed",
        )
        total_processed = (await db.execute(parsed_stmt)).scalar() or 0

        pending_stmt = select(func.count(Resume.id)).where(
            Resume.organization_id == organization_id,
            Resume.parse_status.in_(["pending", "processing"]),
        )
        total_pending = (await db.execute(pending_stmt)).scalar() or 0

        failed_stmt = select(func.count(Resume.id)).where(
            Resume.organization_id == organization_id,
            Resume.parse_status == "failed",
        )
        total_failed = (await db.execute(failed_stmt)).scalar() or 0

        success_rate = round((total_processed / total_uploaded * 100), 1) if total_uploaded > 0 else 0.0

        return ProcessingOverviewResponse(
            total_uploaded=total_uploaded,
            total_processed=total_processed,
            total_pending=total_pending,
            total_failed=total_failed,
            success_rate_percent=success_rate,
        )

    async def get_recruiter_activity(
        self, db: AsyncSession, organization_id: uuid.UUID, limit: int = 20
    ) -> List[DashboardActivityItem]:
        activities: List[DashboardActivityItem] = []

        # 1. Requisitions created
        reqs_stmt = (
            select(Requisition)
            .where(Requisition.organization_id == organization_id)
            .order_by(Requisition.created_at.desc())
            .limit(limit)
        )
        reqs = (await db.execute(reqs_stmt)).scalars().all()
        for r in reqs:
            activities.append(
                DashboardActivityItem(
                    id=f"req_{r.id}",
                    type="requisition_created",
                    title="Requisition Created",
                    description=f"Created requisition '{r.title}' (Status: {r.status})",
                    timestamp=_ensure_utc(r.created_at),
                    entity_id=str(r.id),
                    entity_type="requisition",
                )
            )

        # 2. Upload batches
        batch_stmt = (
            select(UploadBatch)
            .where(UploadBatch.organization_id == organization_id)
            .order_by(UploadBatch.created_at.desc())
            .limit(limit)
        )
        batches = (await db.execute(batch_stmt)).scalars().all()
        for b in batches:
            activities.append(
                DashboardActivityItem(
                    id=f"batch_{b.id}",
                    type="batch_uploaded",
                    title="Resumes Uploaded",
                    description=f"Uploaded {b.total_files} resume(s) (Status: {b.status})",
                    timestamp=_ensure_utc(b.created_at),
                    entity_id=str(b.requisition_id),
                    entity_type="requisition",
                )
            )

        # 3. Completed evaluations
        eval_stmt = (
            select(Evaluation)
            .options(selectinload(Evaluation.candidate))
            .where(
                Evaluation.organization_id == organization_id,
                Evaluation.is_current == True,
                Evaluation.evaluation_status == "COMPLETED",
            )
            .order_by(Evaluation.created_at.desc())
            .limit(limit)
        )
        evals = (await db.execute(eval_stmt)).scalars().all()
        for ev in evals:
            c_name = ev.candidate.full_name if ev.candidate and ev.candidate.full_name else "Candidate"
            score_val = float(ev.total_score) if ev.total_score is not None else 0.0
            activities.append(
                DashboardActivityItem(
                    id=f"eval_{ev.id}",
                    type="evaluation_completed",
                    title="Evaluation Completed",
                    description=f"{c_name} scored {score_val:.1f} / 100 ({ev.confidence_level} confidence)",
                    timestamp=_ensure_utc(ev.created_at),
                    entity_id=str(ev.candidate_id),
                    entity_type="candidate",
                )
            )

        # 4. Recruiter reviews
        rev_stmt = (
            select(RecruiterReview)
            .options(
                selectinload(RecruiterReview.evaluation).selectinload(Evaluation.candidate),
                selectinload(RecruiterReview.recruiter),
            )
            .where(RecruiterReview.organization_id == organization_id)
            .order_by(RecruiterReview.reviewed_at.desc())
            .limit(limit)
        )
        reviews = (await db.execute(rev_stmt)).scalars().all()
        for rev in reviews:
            c_name = "Candidate"
            if rev.evaluation and rev.evaluation.candidate and rev.evaluation.candidate.full_name:
                c_name = rev.evaluation.candidate.full_name
            r_actor = rev.recruiter.email if rev.recruiter else None
            activities.append(
                DashboardActivityItem(
                    id=f"review_{rev.id}",
                    type="review_recorded",
                    title="Review Recorded",
                    description=f"Candidate {c_name} marked as {rev.decision}",
                    timestamp=_ensure_utc(rev.reviewed_at),
                    actor_name=r_actor,
                    entity_id=str(rev.evaluation.candidate_id) if rev.evaluation else None,
                    entity_type="candidate",
                )
            )

        # 5. Candidate notes
        notes_stmt = (
            select(CandidateNote)
            .options(selectinload(CandidateNote.candidate), selectinload(CandidateNote.author))
            .where(CandidateNote.organization_id == organization_id)
            .order_by(CandidateNote.created_at.desc())
            .limit(limit)
        )
        notes = (await db.execute(notes_stmt)).scalars().all()
        for n in notes:
            c_name = n.candidate.full_name if n.candidate and n.candidate.full_name else "Candidate"
            author_actor = n.author.email if n.author else None
            snippet = (n.content[:60] + "...") if len(n.content) > 60 else n.content
            activities.append(
                DashboardActivityItem(
                    id=f"note_{n.id}",
                    type="note_added",
                    title="Internal Note Added",
                    description=f"Note on {c_name}: \"{snippet}\"",
                    timestamp=_ensure_utc(n.created_at),
                    actor_name=author_actor,
                    entity_id=str(n.candidate_id),
                    entity_type="candidate",
                )
            )

        activities.sort(key=lambda a: a.timestamp, reverse=True)
        return activities[:limit]

    async def get_full_dashboard(
        self, db: AsyncSession, organization_id: uuid.UUID
    ) -> RecruiterDashboardResponse:
        metrics = await self.get_dashboard_metrics(db, organization_id)
        reqs = await self.get_requisition_overview(db, organization_id, limit=10)
        processing = await self.get_processing_overview(db, organization_id)
        activities = await self.get_recruiter_activity(db, organization_id, limit=15)
        return RecruiterDashboardResponse(
            metrics=metrics,
            requisitions=reqs,
            processing=processing,
            recent_activity=activities,
        )


dashboard_service = DashboardService()
