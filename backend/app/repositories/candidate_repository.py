from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidate import Candidate, CandidateEducation, CandidateEmployment, CandidateSkill
from app.models.evaluation import Evaluation, RecruiterReview
from app.models.requisition import Requisition
from app.models.resume import Resume


class CandidateRepository:
    """Database repository for candidate profiles and structured records."""

    async def get_candidate_by_id(
        self,
        db: AsyncSession,
        candidate_id: uuid.UUID,
        organization_id: Optional[uuid.UUID] = None,
    ) -> Optional[Candidate]:
        stmt = (
            select(Candidate)
            .where(Candidate.id == candidate_id)
            .options(
                selectinload(Candidate.employments),
                selectinload(Candidate.educations),
                selectinload(Candidate.skills),
                selectinload(Candidate.resumes),
            )
        )
        if organization_id:
            stmt = stmt.where(Candidate.organization_id == organization_id)

        result = await db.execute(stmt)
        return result.scalars().first()

    async def list_candidates(
        self,
        db: AsyncSession,
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
        stmt = select(Candidate).where(Candidate.organization_id == organization_id)

        # 1. Search filter across name, email, location, skills, job title, and company
        if search and search.strip():
            term = f"%{search.strip()}%"
            skill_sub = select(CandidateSkill.candidate_id).where(
                or_(
                    CandidateSkill.name.ilike(term),
                    CandidateSkill.raw_name.ilike(term),
                )
            )
            emp_sub = select(CandidateEmployment.candidate_id).where(
                or_(
                    CandidateEmployment.job_title.ilike(term),
                    CandidateEmployment.company.ilike(term),
                )
            )
            stmt = stmt.where(
                or_(
                    Candidate.full_name.ilike(term),
                    Candidate.email.ilike(term),
                    Candidate.location.ilike(term),
                    Candidate.id.in_(skill_sub),
                    Candidate.id.in_(emp_sub),
                )
            )

        # 2. Requisition association
        if requisition_id:
            req_resume_sub = select(Resume.candidate_id).where(
                Resume.requisition_id == requisition_id,
                Resume.candidate_id.is_not(None),
            )
            req_eval_sub = select(Evaluation.candidate_id).where(
                Evaluation.requisition_id == requisition_id,
            )
            stmt = stmt.where(
                or_(Candidate.id.in_(req_resume_sub), Candidate.id.in_(req_eval_sub))
            )

        # 3. Location filter
        if location and location.strip():
            stmt = stmt.where(Candidate.location.ilike(f"%{location.strip()}%"))

        # 4. Skill filter
        if skill and skill.strip():
            s_term = f"%{skill.strip()}%"
            s_sub = select(CandidateSkill.candidate_id).where(
                or_(CandidateSkill.name.ilike(s_term), CandidateSkill.raw_name.ilike(s_term))
            )
            stmt = stmt.where(Candidate.id.in_(s_sub))

        # 5. Experience filters
        if min_experience is not None:
            stmt = stmt.where(Candidate.total_experience_years >= min_experience)
        if max_experience is not None:
            stmt = stmt.where(Candidate.total_experience_years <= max_experience)

        # 6. Notice period filter
        if max_notice_days is not None:
            stmt = stmt.where(Candidate.notice_period_days <= max_notice_days)

        # 7. Score filters
        if min_score is not None:
            min_score_sub = select(Evaluation.candidate_id).where(
                Evaluation.organization_id == organization_id,
                Evaluation.is_current == True,
                Evaluation.evaluation_status == "COMPLETED",
                Evaluation.total_score >= min_score,
            )
            if requisition_id:
                min_score_sub = min_score_sub.where(Evaluation.requisition_id == requisition_id)
            stmt = stmt.where(Candidate.id.in_(min_score_sub))

        if max_score is not None:
            max_score_sub = select(Evaluation.candidate_id).where(
                Evaluation.organization_id == organization_id,
                Evaluation.is_current == True,
                Evaluation.evaluation_status == "COMPLETED",
                Evaluation.total_score <= max_score,
            )
            if requisition_id:
                max_score_sub = max_score_sub.where(Evaluation.requisition_id == requisition_id)
            stmt = stmt.where(Candidate.id.in_(max_score_sub))

        # 8. Evaluation status filter
        if evaluation_status:
            es = evaluation_status.lower()
            if es == "evaluated":
                eval_sub = select(Evaluation.candidate_id).where(
                    Evaluation.organization_id == organization_id,
                    Evaluation.is_current == True,
                    Evaluation.evaluation_status == "COMPLETED",
                )
                if requisition_id:
                    eval_sub = eval_sub.where(Evaluation.requisition_id == requisition_id)
                stmt = stmt.where(Candidate.id.in_(eval_sub))
            elif es == "pending":
                p_sub = select(Resume.candidate_id).where(
                    Resume.organization_id == organization_id,
                    Resume.parse_status.in_(["pending", "processing"]),
                    Resume.candidate_id.is_not(None),
                )
                stmt = stmt.where(Candidate.id.in_(p_sub))
            elif es == "unreviewed":
                rev_sub = select(RecruiterReview.evaluation_id).where(
                    RecruiterReview.organization_id == organization_id,
                    RecruiterReview.decision != "UNREVIEWED",
                )
                unrev_sub = select(Evaluation.candidate_id).where(
                    Evaluation.organization_id == organization_id,
                    Evaluation.is_current == True,
                    Evaluation.evaluation_status == "COMPLETED",
                    ~Evaluation.id.in_(rev_sub),
                )
                if requisition_id:
                    unrev_sub = unrev_sub.where(Evaluation.requisition_id == requisition_id)
                stmt = stmt.where(Candidate.id.in_(unrev_sub))

        # 9. Review decision filter
        if review_decision:
            rd = review_decision.upper()
            if rd == "UNREVIEWED":
                rev_sub = select(RecruiterReview.evaluation_id).where(
                    RecruiterReview.organization_id == organization_id,
                    RecruiterReview.decision != "UNREVIEWED",
                )
                unrev_sub = select(Evaluation.candidate_id).where(
                    Evaluation.organization_id == organization_id,
                    Evaluation.is_current == True,
                    ~Evaluation.id.in_(rev_sub),
                )
                stmt = stmt.where(Candidate.id.in_(unrev_sub))
            else:
                rev_sub = (
                    select(Evaluation.candidate_id)
                    .join(RecruiterReview, RecruiterReview.evaluation_id == Evaluation.id)
                    .where(
                        Evaluation.organization_id == organization_id,
                        Evaluation.is_current == True,
                        RecruiterReview.decision == rd,
                    )
                )
                if requisition_id:
                    rev_sub = rev_sub.where(Evaluation.requisition_id == requisition_id)
                stmt = stmt.where(Candidate.id.in_(rev_sub))

        # Total count query
        sub = stmt.subquery()
        count_stmt = select(func.count()).select_from(sub)
        count_res = await db.execute(count_stmt)
        total = count_res.scalar() or 0

        # 10. Sorting
        if sort_by in ("score", "evaluation_score"):
            join_cond = and_(
                Evaluation.candidate_id == Candidate.id,
                Evaluation.is_current == True,
            )
            if requisition_id:
                join_cond = and_(join_cond, Evaluation.requisition_id == requisition_id)
            stmt = stmt.outerjoin(Evaluation, join_cond)

            if sort_order == "asc":
                stmt = stmt.order_by(Evaluation.total_score.asc().nulls_last(), Candidate.created_at.desc())
            else:
                stmt = stmt.order_by(Evaluation.total_score.desc().nulls_last(), Candidate.created_at.desc())
        elif sort_by in ("experience", "total_experience_years"):
            if sort_order == "asc":
                stmt = stmt.order_by(Candidate.total_experience_years.asc().nulls_last(), Candidate.created_at.desc())
            else:
                stmt = stmt.order_by(Candidate.total_experience_years.desc().nulls_last(), Candidate.created_at.desc())
        elif sort_by in ("name", "full_name"):
            if sort_order == "asc":
                stmt = stmt.order_by(Candidate.full_name.asc().nulls_last())
            else:
                stmt = stmt.order_by(Candidate.full_name.desc().nulls_last())
        else:
            if sort_order == "asc":
                stmt = stmt.order_by(Candidate.created_at.asc())
            else:
                stmt = stmt.order_by(Candidate.created_at.desc())

        # Pagination
        stmt = (
            stmt.options(
                selectinload(Candidate.skills),
                selectinload(Candidate.employments),
                selectinload(Candidate.resumes),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await db.execute(stmt)
        candidates = list(result.scalars().all())

        if not candidates:
            return [], total

        # Batch load current evaluations and latest reviews for these candidates
        cand_ids = [c.id for c in candidates]
        eval_query = (
            select(Evaluation)
            .options(selectinload(Evaluation.reviews), selectinload(Evaluation.requisition))
            .where(
                Evaluation.candidate_id.in_(cand_ids),
                Evaluation.organization_id == organization_id,
                Evaluation.is_current == True,
            )
        )
        if requisition_id:
            eval_query = eval_query.where(Evaluation.requisition_id == requisition_id)

        eval_res = await db.execute(eval_query)
        evaluations_by_candidate: Dict[uuid.UUID, Evaluation] = {}
        for ev in eval_res.scalars().all():
            # Keep most recent if multiple (or exact requisition match)
            if ev.candidate_id not in evaluations_by_candidate or ev.created_at > evaluations_by_candidate[ev.candidate_id].created_at:
                evaluations_by_candidate[ev.candidate_id] = ev

        # Batch load requisition titles from resumes if not covered by evaluation
        req_ids_to_fetch = set()
        for c in candidates:
            if c.id not in evaluations_by_candidate:
                for r in c.resumes:
                    if r.requisition_id:
                        req_ids_to_fetch.add(r.requisition_id)
        
        req_titles: Dict[uuid.UUID, str] = {}
        if req_ids_to_fetch:
            req_stmt = select(Requisition.id, Requisition.title).where(Requisition.id.in_(req_ids_to_fetch))
            req_res = await db.execute(req_stmt)
            for r_id, r_title in req_res.all():
                req_titles[r_id] = r_title

        enriched_items: List[Dict[str, Any]] = []
        for c in candidates:
            # Primary employment
            curr_emp = next((e for e in c.employments if e.is_current), None)
            if not curr_emp and c.employments:
                curr_emp = c.employments[0]

            primary_title = curr_emp.job_title if curr_emp else None
            primary_comp = curr_emp.company if curr_emp else None

            # Evaluation & Review data
            ev = evaluations_by_candidate.get(c.id)
            eval_score = float(ev.total_score) if ev and ev.total_score is not None else None
            eval_status = ev.evaluation_status if ev else None
            evidence_cov = float(ev.evidence_coverage) if ev and ev.evidence_coverage is not None else None

            review_decision_val = None
            if ev:
                if ev.reviews:
                    latest_review = sorted(ev.reviews, key=lambda r: r.reviewed_at, reverse=True)[0]
                    review_decision_val = latest_review.decision
                elif ev.evaluation_status == "COMPLETED":
                    review_decision_val = "UNREVIEWED"

            # Requisition info
            req_id_val = None
            req_title_val = None
            if ev and ev.requisition:
                req_id_val = ev.requisition.id
                req_title_val = ev.requisition.title
            elif c.resumes:
                first_resume = c.resumes[0]
                req_id_val = first_resume.requisition_id
                if req_id_val:
                    req_title_val = req_titles.get(req_id_val)

            enriched_items.append({
                "id": c.id,
                "organization_id": c.organization_id,
                "full_name": c.full_name,
                "email": c.email,
                "phone": c.phone,
                "location": c.location,
                "notice_period_days": c.notice_period_days,
                "total_experience_years": float(c.total_experience_years) if c.total_experience_years is not None else None,
                "primary_job_title": primary_title,
                "primary_company": primary_comp,
                "evaluation_score": eval_score,
                "evaluation_status": eval_status,
                "review_decision": review_decision_val,
                "evidence_coverage": evidence_cov,
                "requisition_id": req_id_val,
                "requisition_title": req_title_val,
                "skills": c.skills,
                "is_anonymized": getattr(c, "is_anonymized", False),
                "consent_status": getattr(c, "consent_status", "GRANTED"),
                "deletion_status": getattr(c, "deletion_status", None),
                "created_at": c.created_at,
            })

        return enriched_items, total


candidate_repository = CandidateRepository()
