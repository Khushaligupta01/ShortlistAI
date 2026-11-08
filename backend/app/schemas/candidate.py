from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class CandidateSkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    raw_name: str
    evidence: Optional[str] = None


class CandidateEmploymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company: str
    job_title: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: bool = False
    description: Optional[str] = None
    technologies: Optional[List[str]] = None


class CandidateEducationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    institution: str
    qualification: Optional[str] = None
    field_of_study: Optional[str] = None
    graduation_year: Optional[int] = None


class CandidateResumeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    file_name: str
    mime_type: str
    file_size_bytes: int
    parse_status: str
    created_at: datetime


class CandidateListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    notice_period_days: Optional[int] = None
    total_experience_years: Optional[float] = None
    skills: List[CandidateSkillOut] = []
    created_at: datetime


class CandidateDetailResponse(CandidateListItemResponse):
    certifications: Optional[List[Dict[str, Any]]] = None
    parsed_profile_json: Optional[Dict[str, Any]] = None
    employments: List[CandidateEmploymentOut] = []
    educations: List[CandidateEducationOut] = []
    resumes: List[CandidateResumeOut] = []


class CandidateListResponse(BaseModel):
    items: List[CandidateListItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
