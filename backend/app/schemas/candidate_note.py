from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CandidateNoteCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    requisition_id: Optional[uuid.UUID] = None


class CandidateNoteUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


class CandidateNoteResponse(BaseModel):
    id: str
    candidate_id: str
    requisition_id: Optional[str] = None
    requisition_title: Optional[str] = None
    author_id: str
    author_name: Optional[str] = None
    author_email: Optional[str] = None
    organization_id: str
    content: str
    created_at: datetime
    updated_at: datetime
    is_author: bool = False

    model_config = ConfigDict(from_attributes=True)


class CandidateNoteListResponse(BaseModel):
    notes: List[CandidateNoteResponse]
    total: int

    model_config = ConfigDict(from_attributes=True)
