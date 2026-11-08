from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidate import Candidate, CandidateEducation, CandidateEmployment, CandidateSkill
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
    ) -> Tuple[List[Candidate], int]:
        stmt = select(Candidate).where(Candidate.organization_id == organization_id)

        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    Candidate.full_name.ilike(pattern),
                    Candidate.email.ilike(pattern),
                    Candidate.location.ilike(pattern),
                )
            )

        if location:
            stmt = stmt.where(Candidate.location.ilike(f"%{location.strip()}%"))

        if requisition_id:
            # Subquery on resumes table
            req_sub = select(Resume.candidate_id).where(
                Resume.requisition_id == requisition_id,
                Resume.candidate_id.is_not(None),
            )
            stmt = stmt.where(Candidate.id.in_(req_sub))

        if skill:
            skill_sub = select(CandidateSkill.candidate_id).where(
                CandidateSkill.name.ilike(f"%{skill.strip().lower()}%")
            )
            stmt = stmt.where(Candidate.id.in_(skill_sub))

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_res = await db.execute(count_stmt)
        total = count_res.scalar() or 0

        # Paginate and load relationships
        stmt = (
            stmt.options(
                selectinload(Candidate.skills),
                selectinload(Candidate.employments),
                selectinload(Candidate.resumes),
            )
            .order_by(Candidate.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await db.execute(stmt)
        items = list(result.scalars().all())
        return items, total


candidate_repository = CandidateRepository()

