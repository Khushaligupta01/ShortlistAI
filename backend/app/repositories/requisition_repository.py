from __future__ import annotations

import uuid
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.requisition import Requisition


class RequisitionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id_and_org(
        self, requisition_id: uuid.UUID, org_id: uuid.UUID
    ) -> Optional[Requisition]:
        result = await self.db.execute(
            select(Requisition).where(
                Requisition.id == requisition_id,
                Requisition.organization_id == org_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_org(
        self,
        org_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
    ) -> Tuple[List[Requisition], int]:
        query = select(Requisition).where(
            Requisition.organization_id == org_id
        )
        if status:
            query = query.where(Requisition.status == status)

        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()

        query = (
            query.order_by(Requisition.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all()), total
