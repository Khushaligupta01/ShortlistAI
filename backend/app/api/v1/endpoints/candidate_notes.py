from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user, require_role
from app.db.session import get_db
from app.models.candidate_note import CandidateNote
from app.schemas.auth import CurrentUserResponse
from app.schemas.candidate_note import (
    CandidateNoteCreate,
    CandidateNoteListResponse,
    CandidateNoteResponse,
    CandidateNoteUpdate,
)
from app.services.candidate_note_service import candidate_note_service

router = APIRouter(tags=["candidate-notes"])

_RECRUITER_OR_INTERNAL = require_role("recruiter", "delivery_head", "admin", "super_admin")


def _note_to_response(note: CandidateNote, current_user_id: uuid.UUID) -> CandidateNoteResponse:
    author_name = None
    author_email = None
    if note.author:
        author_name = getattr(note.author, "full_name", None) or getattr(note.author, "email", None)
        author_email = getattr(note.author, "email", None)

    req_title = None
    if note.requisition:
        req_title = note.requisition.title

    return CandidateNoteResponse(
        id=str(note.id),
        candidate_id=str(note.candidate_id),
        requisition_id=str(note.requisition_id) if note.requisition_id else None,
        requisition_title=req_title,
        author_id=str(note.author_id),
        author_name=author_name,
        author_email=author_email,
        organization_id=str(note.organization_id),
        content=note.content,
        created_at=note.created_at,
        updated_at=note.updated_at,
        is_author=(note.author_id == current_user_id),
    )


@router.get("/candidates/{candidate_id}/notes", response_model=CandidateNoteListResponse)
async def list_candidate_notes(
    candidate_id: uuid.UUID,
    current_user: CurrentUserResponse = _RECRUITER_OR_INTERNAL,
    db: AsyncSession = Depends(get_db),
) -> CandidateNoteListResponse:
    if not current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organization context.")

    org_id = uuid.UUID(current_user.organization_id)
    user_id = uuid.UUID(current_user.id)

    notes = await candidate_note_service.list_notes(
        db=db,
        candidate_id=candidate_id,
        organization_id=org_id,
    )
    return CandidateNoteListResponse(
        notes=[_note_to_response(n, user_id) for n in notes],
        total=len(notes),
    )


@router.post(
    "/candidates/{candidate_id}/notes",
    response_model=CandidateNoteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_candidate_note(
    candidate_id: uuid.UUID,
    payload: CandidateNoteCreate,
    current_user: CurrentUserResponse = _RECRUITER_OR_INTERNAL,
    db: AsyncSession = Depends(get_db),
) -> CandidateNoteResponse:
    if not current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organization context.")

    org_id = uuid.UUID(current_user.organization_id)
    user_id = uuid.UUID(current_user.id)

    note = await candidate_note_service.create_note(
        db=db,
        candidate_id=candidate_id,
        author_id=user_id,
        organization_id=org_id,
        content=payload.content,
        requisition_id=payload.requisition_id,
    )
    return _note_to_response(note, user_id)


@router.put("/candidates/notes/{note_id}", response_model=CandidateNoteResponse)
async def update_candidate_note(
    note_id: uuid.UUID,
    payload: CandidateNoteUpdate,
    current_user: CurrentUserResponse = _RECRUITER_OR_INTERNAL,
    db: AsyncSession = Depends(get_db),
) -> CandidateNoteResponse:
    if not current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organization context.")

    org_id = uuid.UUID(current_user.organization_id)
    user_id = uuid.UUID(current_user.id)
    user_role = current_user.role or "recruiter"

    note = await candidate_note_service.update_note(
        db=db,
        note_id=note_id,
        user_id=user_id,
        user_role=user_role,
        organization_id=org_id,
        new_content=payload.content,
    )
    return _note_to_response(note, user_id)


@router.delete("/candidates/notes/{note_id}")
async def delete_candidate_note(
    note_id: uuid.UUID,
    current_user: CurrentUserResponse = _RECRUITER_OR_INTERNAL,
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organization context.")

    org_id = uuid.UUID(current_user.organization_id)
    user_id = uuid.UUID(current_user.id)
    user_role = current_user.role or "recruiter"

    await candidate_note_service.delete_note(
        db=db,
        note_id=note_id,
        user_id=user_id,
        user_role=user_role,
        organization_id=org_id,
    )
    return {"ok": True, "message": "Note deleted successfully"}
