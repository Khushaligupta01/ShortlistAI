from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class UploadBatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    requisition_id: uuid.UUID
    organization_id: uuid.UUID
    total_files: int
    accepted_files: int
    rejected_files: int
    duplicate_files: int
    processing_files: int
    completed_files: int
    failed_files: int
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None


class ResumeFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    file_name: str
    mime_type: str
    file_size_bytes: int
    parse_status: str
    extraction_status: str
    error_code: Optional[str] = None
    error_message_safe: Optional[str] = None
    candidate_id: Optional[uuid.UUID] = None
    duplicate_of_id: Optional[uuid.UUID] = None
    duplicate_type: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None


class ResumeDetailResponse(ResumeFileResponse):
    raw_text: Optional[str] = None
    normalized_text: Optional[str] = None
    duplicate_details: Optional[Dict[str, Any]] = None


class ResumeReviewRequest(BaseModel):
    full_name: Optional[str] = Field(None, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    location: Optional[str] = Field(None, max_length=255)
    notice_period_days: Optional[int] = Field(None, ge=0, le=365)
    skills: Optional[List[str]] = Field(None, max_length=50)

