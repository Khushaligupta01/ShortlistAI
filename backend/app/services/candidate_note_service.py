from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidate import Candidate
from app.models.candidate_note import CandidateNote
from app.models.requisition import Requisition


class CandidateNoteService:
    async def create_note(
        self,
        db: AsyncSession,
        candidate_id: uuid.UUID,
        author_id: uuid.UUID,
        organization_id: uuid.UUID,
        content: str,
        requisition_id: Optional[uuid.UUID] = None,
    ) -> CandidateNote:
        # Verify candidate exists in organization
        cand_stmt = select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.organization_id == organization_id,
        )
        cand_res = await db.execute(cand_stmt)
        candidate = cand_res.scalar_one_or_none()
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate {candidate_id} not found in this organization",
            )

        # If requisition_id provided, verify it belongs to organization
        if requisition_id:
            req_stmt = select(Requisition).where(
                Requisition.id == requisition_id,
                Requisition.organization_id == organization_id,
            )
            req_res = await db.execute(req_stmt)
            if not req_res.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Requisition {requisition_id} not found in this organization",
                )

        note = CandidateNote(
            id=uuid.uuid4(),
            candidate_id=candidate_id,
            requisition_id=requisition_id,
            author_id=author_id,
            organization_id=organization_id,
            content=content.strip(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(note)
        await db.commit()
        await db.refresh(note)

        # Reload with relationships
        stmt = (
            select(CandidateNote)
            .options(selectinload(CandidateNote.author), selectinload(CandidateNote.requisition))
            .where(CandidateNote.id == note.id)
        )
        res = await db.execute(stmt)
        return res.scalar_one()

    async def list_notes(
        self,
        db: AsyncSession,
        candidate_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> List[CandidateNote]:
        stmt = (
            select(CandidateNote)
            .options(selectinload(CandidateNote.author), selectinload(CandidateNote.requisition))
            .where(
                CandidateNote.candidate_id == candidate_id,
                CandidateNote.organization_id == organization_id,
            )
            .order_by(CandidateNote.created_at.desc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def get_note_by_id(
        self,
        db: AsyncSession,
        note_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> Optional[CandidateNote]:
        stmt = (
            select(CandidateNote)
            .options(selectinload(CandidateNote.author), selectinload(CandidateNote.requisition))
            .where(
                CandidateNote.id == note_id,
                CandidateNote.organization_id == organization_id,
            )
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def update_note(
        self,
        db: AsyncSession,
        note_id: uuid.UUID,
        user_id: uuid.UUID,
        user_role: str,
        organization_id: uuid.UUID,
        new_content: str,
    ) -> CandidateNote:
        note = await self.get_note_by_id(db, note_id, organization_id)
        if not note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Note {note_id} not found",
            )

        # Check permission: only author or privileged roles (admin, delivery_head) can edit
        is_author = note.author_id == user_id
        is_privileged = user_role in ("admin", "delivery_head", "super_admin")
        if not (is_author or is_privileged):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to edit this note",
            )

        note.content = new_content.strip()
        note.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(note)

        # Reload with relationships
        stmt = (
            select(CandidateNote)
            .options(selectinload(CandidateNote.author), selectinload(CandidateNote.requisition))
            .where(CandidateNote.id == note.id)
        )
        res = await db.execute(stmt)
        return res.scalar_one()

    async def delete_note(
        self,
        db: AsyncSession,
        note_id: uuid.UUID,
        user_id: uuid.UUID,
        user_role: str,
        organization_id: uuid.UUID,
    ) -> bool:
        note = await self.get_note_by_id(db, note_id, organization_id)
        if not note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Note {note_id} not found",
            )

        is_author = note.author_id == user_id
        is_privileged = user_role in ("admin", "delivery_head", "super_admin")
        if not (is_author or is_privileged):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this note",
            )

        await db.delete(note)
        await db.commit()
        return True


candidate_note_service = CandidateNoteService()

