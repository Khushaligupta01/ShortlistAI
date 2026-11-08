from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.evidence_extraction_service import evidence_extraction_service
from app.ai.schemas import CriterionEvidenceItem
from app.core.config import settings
from app.db.session import async_session_factory
from app.models.candidate import Candidate
from app.models.evaluation import Evaluation, EvaluationEvidence, EvaluationRun, RecruiterReview
from app.models.requisition import Requisition
from app.models.resume import Resume
from app.models.scorecard import Scorecard
from app.services.scoring_engine_service import scoring_engine

logger = logging.getLogger("shortlistai.evaluation_service")


class EvaluationService:
    """
    Orchestrates candidate evaluations, batch evaluation runs, deterministic recalculations,
    and recruiter reviews.
    """

    async def get_approved_scorecard(
        self,
        db: AsyncSession,
        requisition_id: uuid.UUID,
    ) -> Optional[Scorecard]:
        """
        Loads the active approved scorecard for a requisition.
        """
        stmt = (
            select(Scorecard)
            .where(
                and_(
                    Scorecard.requisition_id == requisition_id,
                    Scorecard.status.in_(["approved", "active"]),
                )
            )
            .order_by(Scorecard.version_number.desc())
            .options(selectinload(Scorecard.criteria))
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def evaluate_candidate(
        self,
        db: AsyncSession,
        requisition_id: uuid.UUID,
        candidate_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        evaluation_run_id: Optional[uuid.UUID] = None,
    ) -> Evaluation:
        """
        Evaluates a single candidate against the approved scorecard of a requisition.
        Guarantees deterministic scoring and audit versioning.
        """
        # 1. Verify approved scorecard
        scorecard = await self.get_approved_scorecard(db, requisition_id)
        if not scorecard:
            raise ValueError("Requisition does not have an approved scorecard. Evaluation cannot proceed.")

        # 2. Verify candidate ownership and privacy/consent status
        c_stmt = (
            select(Candidate)
            .where(
                and_(
                    Candidate.id == candidate_id,
                    Candidate.organization_id == organization_id,
                )
            )
            .options(
                selectinload(Candidate.skills),
                selectinload(Candidate.employments),
                selectinload(Candidate.educations),
                selectinload(Candidate.resumes),
            )
        )
        c_res = await db.execute(c_stmt)
        candidate = c_res.scalars().first()
        if not candidate:
            raise ValueError(f"Candidate {candidate_id} not found in organization.")

        # Check candidate consent and deletion status
        from app.services.consent_service import is_processing_allowed
        allowed, reason = is_processing_allowed(candidate)
        if not allowed:
            from app.services.audit_service import log_event
            await log_event(
                db=db,
                organization_id=organization_id,
                actor_user_id=user_id,
                event_type="PROCESSING_BLOCKED_CONSENT",
                resource_type="candidate",
                resource_id=candidate.id,
                payload={"reason": reason, "requisition_id": str(requisition_id)},
                commit=True,
            )
            raise ValueError(f"Processing blocked: {reason}")

        # 3. Retrieve supporting resume text
        resume_text = ""
        for r in candidate.resumes or []:
            if r.requisition_id == requisition_id and (r.raw_text or r.normalized_text):
                resume_text = r.raw_text or r.normalized_text
                break
        if not resume_text and candidate.resumes:
            # Fallback to any extracted resume text for this candidate
            for r in candidate.resumes:
                if r.raw_text or r.normalized_text:
                    resume_text = r.raw_text or r.normalized_text
                    break

        # 4. Extract evidence
        evidence_items = await evidence_extraction_service.extract_evidence(
            candidate=candidate,
            criteria=scorecard.criteria or [],
            resume_text=resume_text,
        )

        # 5. Deterministic Scoring
        scoring_res = scoring_engine.compute_scores(
            candidate=candidate,
            scorecard=scorecard,
            evidence_items=evidence_items,
        )

        now = datetime.now(timezone.utc)

        # 6. Deactivate existing current evaluations for this requisition to preserve history
        existing_stmt = (
            select(Evaluation)
            .where(
                and_(
                    Evaluation.candidate_id == candidate_id,
                    Evaluation.requisition_id == requisition_id,
                    Evaluation.is_current == True,
                )
            )
            .order_by(Evaluation.version_number.desc())
        )
        existing_res = await db.execute(existing_stmt)
        old_eval = existing_res.scalars().first()

        next_version = (old_eval.version_number + 1) if old_eval else 1

        if old_eval:
            old_eval.is_current = False

        # 7. Create new Evaluation record
        evaluation = Evaluation(
            candidate_id=candidate_id,
            requisition_id=requisition_id,
            scorecard_id=scorecard.id,
            organization_id=organization_id,
            evaluation_run_id=evaluation_run_id,
            total_score=scoring_res.normalized_score,
            raw_score=scoring_res.raw_score,
            normalized_score=scoring_res.normalized_score,
            evidence_coverage=scoring_res.evidence_coverage,
            confidence_level=scoring_res.confidence_level,
            evaluation_status="COMPLETED",
            version_number=next_version,
            scorecard_version=scorecard.version_number,
            is_current=True,
            score_breakdown_json=scoring_res.breakdown_json,
            model_provider=settings.AI_PROVIDER,
            model_name=settings.AI_MODEL,
            evaluated_at=now,
        )
        db.add(evaluation)
        await db.flush()

        # 8. Create EvaluationEvidence records
        for cr in scoring_res.criteria_results:
            # Match back to scorecard_criterion_id
            crit_uuid = None
            try:
                crit_uuid = uuid.UUID(cr.criterion_id)
            except (ValueError, TypeError):
                # If direct criterion, match by name or pick first
                if scorecard.criteria:
                    crit_uuid = scorecard.criteria[0].id

            if crit_uuid:
                ev_rec = EvaluationEvidence(
                    evaluation_id=evaluation.id,
                    scorecard_criterion_id=crit_uuid,
                    evidence_status=cr.match_status,
                    confidence_score=cr.confidence,
                    awarded_points=cr.awarded_points,
                    maximum_points=cr.maximum_points,
                    evidence_text=cr.evidence_text,
                    source_reference=cr.source_reference,
                    explanation=cr.explanation,
                    flags_json=cr.flags,
                    source_excerpts_json=[cr.evidence_text] if cr.evidence_text else [],
                )
                db.add(ev_rec)

        await db.commit()
        await db.refresh(evaluation)
        return evaluation

    async def start_batch_evaluation(
        self,
        db: AsyncSession,
        requisition_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        candidate_ids: Optional[List[uuid.UUID]] = None,
    ) -> EvaluationRun:
        """
        Initiates a batch evaluation run for a requisition and launches background processing.
        """
        scorecard = await self.get_approved_scorecard(db, requisition_id)
        if not scorecard:
            raise ValueError("Requisition does not have an approved scorecard. Evaluation cannot proceed.")

        # Determine eligible candidate IDs
        if candidate_ids:
            cand_stmt = (
                select(Candidate.id)
                .where(
                    and_(
                        Candidate.id.in_(candidate_ids),
                        Candidate.organization_id == organization_id,
                    )
                )
            )
        else:
            # Find all candidates with resumes linked to this requisition
            cand_stmt = (
                select(Candidate.id)
                .join(Resume, Candidate.id == Resume.candidate_id)
                .where(
                    and_(
                        Resume.requisition_id == requisition_id,
                        Candidate.organization_id == organization_id,
                    )
                )
                .distinct()
            )

        cand_res = await db.execute(cand_stmt)
        target_ids = list(cand_res.scalars().all())

        if not target_ids:
            # Fallback to all candidates in org if none explicitly tied to requisition yet
            fallback_stmt = (
                select(Candidate.id)
                .where(Candidate.organization_id == organization_id)
                .limit(50)
            )
            fb_res = await db.execute(fallback_stmt)
            target_ids = list(fb_res.scalars().all())

        # Create EvaluationRun
        now = datetime.now(timezone.utc)
        run = EvaluationRun(
            requisition_id=requisition_id,
            organization_id=organization_id,
            initiated_by=user_id,
            total_candidates=len(target_ids),
            completed_count=0,
            failed_count=0,
            status="PROCESSING" if target_ids else "COMPLETED",
            started_at=now,
            completed_at=now if not target_ids else None,
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)

        if target_ids:
            # Launch background worker task
            asyncio.create_task(
                self._run_batch_background(
                    run_id=run.id,
                    requisition_id=requisition_id,
                    organization_id=organization_id,
                    user_id=user_id,
                    candidate_ids=target_ids,
                )
            )

        return run

    async def _run_batch_background(
        self,
        run_id: uuid.UUID,
        requisition_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        candidate_ids: List[uuid.UUID],
    ) -> None:
        """
        Background task processing batch evaluations with bounded concurrency.
        Guarantees that a single candidate failure does not abort the batch.
        """
        semaphore = asyncio.Semaphore(5)
        completed = 0
        failed = 0
        errors: List[Dict[str, str]] = []

        async def process_one(cid: uuid.UUID) -> None:
            nonlocal completed, failed
            async with semaphore:
                try:
                    async with self.session_factory() as session:
                        await self.evaluate_candidate(
                            db=session,
                            requisition_id=requisition_id,
                            candidate_id=cid,
                            organization_id=organization_id,
                            user_id=user_id,
                            evaluation_run_id=run_id,
                        )
                    completed += 1
                except Exception as exc:
                    logger.exception(f"Candidate {cid} evaluation failed: {exc}")
                    failed += 1
                    errors.append({"candidate_id": str(cid), "error": str(exc)})

                # Update run progress periodically
                try:
                    async with self.session_factory() as session:
                        await session.execute(
                            update(EvaluationRun)
                            .where(EvaluationRun.id == run_id)
                            .values(
                                completed_count=completed,
                                failed_count=failed,
                            )
                        )
                        await session.commit()
                except Exception:
                    pass

        tasks = [process_one(cid) for cid in candidate_ids]
        await asyncio.gather(*tasks, return_exceptions=True)

        # Finalize EvaluationRun
        final_status = "COMPLETED" if failed == 0 else ("PARTIALLY_FAILED" if completed > 0 else "FAILED")
        async with self.session_factory() as session:
            await session.execute(
                update(EvaluationRun)
                .where(EvaluationRun.id == run_id)
                .values(
                    status=final_status,
                    completed_count=completed,
                    failed_count=failed,
                    error_summary={"errors": errors} if errors else None,
                    completed_at=datetime.now(timezone.utc),
                )
            )
            await session.commit()

    async def recalculate_evaluation(
        self,
        db: AsyncSession,
        evaluation_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> Evaluation:
        """
        Recalculates deterministic scores using the exact same validated evidence
        and scorecard version without re-invoking the AI provider.
        """
        stmt = (
            select(Evaluation)
            .where(
                and_(
                    Evaluation.id == evaluation_id,
                    or_(
                        Evaluation.organization_id == organization_id,
                        Evaluation.organization_id.is_(None),
                    ),
                )
            )
            .options(
                selectinload(Evaluation.candidate).selectinload(Candidate.skills),
                selectinload(Evaluation.candidate).selectinload(Candidate.employments),
                selectinload(Evaluation.scorecard).selectinload(Scorecard.criteria),
                selectinload(Evaluation.evidence),
            )
        )
        res = await db.execute(stmt)
        evaluation = res.scalars().first()
        if not evaluation:
            raise ValueError("Evaluation not found or unauthorized.")

        # Re-construct CriterionEvidenceItem objects from stored evidence records
        evidence_items: List[CriterionEvidenceItem] = []
        for ev in evaluation.evidence:
            evidence_items.append(
                CriterionEvidenceItem(
                    criterion_id=str(ev.scorecard_criterion_id),
                    criterion_name=ev.criterion.criterion_name if ev.criterion else "Criterion",
                    match_status=ev.evidence_status,  # type: ignore
                    evidence_text=ev.evidence_text,
                    source_reference=ev.source_reference,
                    confidence=float(ev.confidence_score),
                    explanation=ev.explanation,
                )
            )

        # Recompute scores deterministically
        scoring_res = scoring_engine.compute_scores(
            candidate=evaluation.candidate,
            scorecard=evaluation.scorecard,
            evidence_items=evidence_items,
        )

        evaluation.total_score = scoring_res.normalized_score
        evaluation.raw_score = scoring_res.raw_score
        evaluation.normalized_score = scoring_res.normalized_score
        evaluation.evidence_coverage = scoring_res.evidence_coverage
        evaluation.confidence_level = scoring_res.confidence_level
        evaluation.score_breakdown_json = scoring_res.breakdown_json
        evaluation.evaluated_at = datetime.now(timezone.utc)

        # Update evidence records awarded points
        crit_res_by_id = {cr.criterion_id: cr for cr in scoring_res.criteria_results}
        for ev in evaluation.evidence:
            cid = str(ev.scorecard_criterion_id)
            if cid in crit_res_by_id:
                cr = crit_res_by_id[cid]
                ev.awarded_points = cr.awarded_points
                ev.maximum_points = cr.maximum_points

        await db.commit()
        await db.refresh(evaluation)
        return evaluation

    async def record_recruiter_review(
        self,
        db: AsyncSession,
        evaluation_id: uuid.UUID,
        recruiter_id: uuid.UUID,
        organization_id: uuid.UUID,
        decision: str,
        notes: Optional[str] = None,
    ) -> RecruiterReview:
        """
        Saves a recruiter review decision (SHORTLIST, REJECT, HOLD, REQUEST_INFO)
        and feedback note on an evaluation.
        """
        # Verify evaluation
        stmt = (
            select(Evaluation)
            .where(
                and_(
                    Evaluation.id == evaluation_id,
                    or_(
                        Evaluation.organization_id == organization_id,
                        Evaluation.organization_id.is_(None),
                    ),
                )
            )
        )
        res = await db.execute(stmt)
        evaluation = res.scalars().first()
        if not evaluation:
            raise ValueError("Evaluation not found or unauthorized.")

        valid_decisions = {"SHORTLIST", "REJECT", "HOLD", "REQUEST_INFO"}
        if decision.upper() not in valid_decisions:
            raise ValueError(f"Invalid decision '{decision}'. Must be one of: {valid_decisions}")

        review = RecruiterReview(
            evaluation_id=evaluation_id,
            recruiter_id=recruiter_id,
            organization_id=organization_id,
            decision=decision.upper(),
            notes=notes,
            reviewed_at=datetime.now(timezone.utc),
        )
        db.add(review)
        await db.commit()
        await db.refresh(review)
        return review


evaluation_service = EvaluationService()
