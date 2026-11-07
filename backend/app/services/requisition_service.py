from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError, ValidationError
from app.models.audit import AuditLog
from app.models.requisition import Requisition
from app.repositories.requisition_repository import RequisitionRepository
from app.schemas.requisition import RequisitionCreate, RequisitionResponse


class RequisitionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = RequisitionRepository(db)

    async def create(
        self,
        data: RequisitionCreate,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Requisition:
        req = Requisition(
            organization_id=org_id,
            created_by=user_id,
            title=data.title,
            job_description=data.job_description,
            location=data.location,
            status="draft",
        )
        await self.repo.create(req)

        # Audit log
        self.db.add(AuditLog(
            organization_id=org_id,
            actor_user_id=user_id,
            event_type="REQUISITION_CREATED",
            resource_type="requisition",
            resource_id=req.id,
            payload_json={"title": data.title},
        ))
        await self.db.commit()
        await self.db.refresh(req)
        return req

    async def get(
        self, requisition_id: uuid.UUID, org_id: uuid.UUID
    ) -> Requisition:
        req = await self.repo.get_by_id_and_org(requisition_id, org_id)
        if not req:
            raise NotFoundError("Requisition not found")
        return req

    async def list(
        self,
        org_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[Requisition], int]:
        return await self.repo.list_by_org(
            org_id=org_id,
            page=page,
            page_size=page_size,
            status=status,
            search=search,
        )
