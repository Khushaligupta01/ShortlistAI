from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.scorecard import Scorecard, ScorecardCriterion


class ScorecardRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_active_for_requisition(
        self, requisition_id: uuid.UUID
    ) -> Optional[Scorecard]:
        result = await self.db.execute(
            select(Scorecard)
            .options(selectinload(Scorecard.criteria))
            .where(
                Scorecard.requisition_id == requisition_id,
                Scorecard.status.in_(["draft", "approved"]),
            )
            .order_by(Scorecard.version_number.desc())
        )
        return result.scalars().first()

    async def get_by_id(self, scorecard_id: uuid.UUID) -> Optional[Scorecard]:
        result = await self.db.execute(
            select(Scorecard)
            .options(selectinload(Scorecard.criteria))
            .where(Scorecard.id == scorecard_id)
        )
        return result.scalar_one_or_none()

    async def get_latest_version_number(self, requisition_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(Scorecard.version_number)
            .where(Scorecard.requisition_id == requisition_id)
            .order_by(Scorecard.version_number.desc())
        )
        row = result.scalars().first()
        return row or 0

    async def create(self, scorecard: Scorecard) -> Scorecard:
        self.db.add(scorecard)
        await self.db.flush()
        await self.db.refresh(scorecard)
        return scorecard

    async def delete_criteria(self, scorecard_id: uuid.UUID) -> None:
        result = await self.db.execute(
            select(ScorecardCriterion).where(
                ScorecardCriterion.scorecard_id == scorecard_id
            )
        )
        for c in result.scalars().all():
            await self.db.delete(c)
        await self.db.flush()
