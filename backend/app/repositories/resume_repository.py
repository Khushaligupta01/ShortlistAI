from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.resume import Resume, ResumeProcessingJob, UploadBatch


class ResumeRepository:
    """Database repository for resume batches, resumes, and processing jobs."""

    async def get_batch_by_id(
        self,
        db: AsyncSession,
        batch_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> Optional[UploadBatch]:
        stmt = (
            select(UploadBatch)
            .where(
                UploadBatch.id == batch_id,
                UploadBatch.organization_id == organization_id,
            )
            .options(selectinload(UploadBatch.resumes))
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_resumes_by_batch(
        self,
        db: AsyncSession,
        batch_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> List[Resume]:
        stmt = (
            select(Resume)
            .where(
                Resume.upload_batch_id == batch_id,
                Resume.organization_id == organization_id,
            )
            .options(selectinload(Resume.candidate))
            .order_by(Resume.created_at.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_resume_by_id(
        self,
        db: AsyncSession,
        resume_id: uuid.UUID,
        organization_id: Optional[uuid.UUID] = None,
    ) -> Optional[Resume]:
        stmt = (
            select(Resume)
            .where(Resume.id == resume_id)
            .options(
                selectinload(Resume.candidate),
                selectinload(Resume.upload_batch),
            )
        )
        if organization_id:
            stmt = stmt.where(Resume.organization_id == organization_id)

        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_resumes_by_requisition(
        self,
        db: AsyncSession,
        requisition_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> List[Resume]:
        stmt = (
            select(Resume)
            .where(
                Resume.requisition_id == requisition_id,
                Resume.organization_id == organization_id,
            )
            .options(selectinload(Resume.candidate))
            .order_by(Resume.created_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def create_batch(self, db: AsyncSession, batch: UploadBatch) -> UploadBatch:
        db.add(batch)
        await db.commit()
        await db.refresh(batch)
        return batch

    async def create_resume(self, db: AsyncSession, resume: Resume) -> Resume:
        db.add(resume)
        await db.commit()
        await db.refresh(resume)
        return resume

    async def create_job(self, db: AsyncSession, job: ResumeProcessingJob) -> ResumeProcessingJob:
        db.add(job)
        await db.commit()
        await db.refresh(job)
        return job


resume_repository = ResumeRepository()
