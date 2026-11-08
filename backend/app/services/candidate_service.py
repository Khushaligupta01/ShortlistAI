from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.organization import OrganizationMembership
from app.models.user import User
from app.repositories.candidate_repository import candidate_repository


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
    def _mask_candidate_if_needed(candidate: Candidate, role: str) -> None:
        """Mask PII (email, phone) for client users per privacy requirements."""
        if role.startswith("client"):
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
    ) -> Tuple[List[Candidate], int]:
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


candidate_service = CandidateService()

