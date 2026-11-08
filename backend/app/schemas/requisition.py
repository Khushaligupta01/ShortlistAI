from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


# ── Requisition schemas ──────────────────────────────────────────────────────

class RequisitionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    job_description: Optional[str] = Field(None, max_length=50000)
    description: Optional[str] = Field(None, max_length=50000)
    location: Optional[str] = Field(None, max_length=255)

    @model_validator(mode="after")
    def resolve_job_description(self) -> "RequisitionCreate":
        jd = self.job_description or self.description
        if not jd or len(jd.strip()) < 10:
            raise ValueError("job_description (or description) must be at least 10 characters")
        self.job_description = jd.strip()
        return self


class RequisitionResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    created_by: uuid.UUID
    title: str
    job_description: str
    location: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    version: int

    @property
    def description(self) -> str:
        return self.job_description

    model_config = {"from_attributes": True}


class RequisitionListResponse(BaseModel):
    items: List[RequisitionResponse]
    total: int
    page: int
    page_size: int


# ── Scorecard criterion schemas ──────────────────────────────────────────────

class CriterionCreate(BaseModel):
    criterion_type: str = Field(..., max_length=30)
    criterion_name: str = Field(..., min_length=1, max_length=255)
    normalized_name: Optional[str] = Field(None, max_length=255)
    label: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    weight: int = Field(0, ge=0, le=100)
    is_mandatory: bool = True
    evidence_from_jd: Optional[str] = Field(None, max_length=2000)
    display_order: int = Field(0, ge=0)
    config_json: Optional[dict] = None


class CriterionResponse(BaseModel):
    id: uuid.UUID
    scorecard_id: uuid.UUID
    criterion_type: str
    criterion_name: str
    normalized_name: Optional[str] = None
    label: str
    description: Optional[str] = None
    weight: int
    is_mandatory: bool
    evidence_from_jd: Optional[str] = None
    display_order: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Scoring config schemas ───────────────────────────────────────────────────

class ScoringConfigRequest(BaseModel):
    experience: int = Field(30, ge=0, le=100)
    must_have_skills: int = Field(40, ge=0, le=100)
    notice_period: int = Field(15, ge=0, le=100)
    location: int = Field(10, ge=0, le=100)
    nice_to_have_skills: int = Field(5, ge=0, le=100)


# ── Scorecard schemas ────────────────────────────────────────────────────────

class ScorecardCreate(BaseModel):
    experience_min: Optional[int] = Field(None, ge=0, le=50)
    experience_max: Optional[int] = Field(None, ge=0, le=60)
    location: Optional[str] = Field(None, max_length=255)
    max_notice_days: Optional[int] = Field(None, ge=0, le=365)
    scoring_config: Optional[ScoringConfigRequest] = None
    criteria: List[CriterionCreate] = Field(default_factory=list)
    jd_extraction_json: Optional[dict] = None


class ScorecardUpdate(BaseModel):
    experience_min: Optional[int] = Field(None, ge=0, le=50)
    experience_max: Optional[int] = Field(None, ge=0, le=60)
    location: Optional[str] = Field(None, max_length=255)
    max_notice_days: Optional[int] = Field(None, ge=0, le=365)
    scoring_config: Optional[ScoringConfigRequest] = None
    criteria: Optional[List[CriterionCreate]] = None


class ScorecardResponse(BaseModel):
    id: uuid.UUID
    requisition_id: uuid.UUID
    version_number: int
    version: Optional[int] = None
    status: str
    experience_min: Optional[int] = None
    experience_max: Optional[int] = None
    location: Optional[str] = None
    max_notice_days: Optional[int] = None
    scoring_config: Optional[dict] = None
    scoring_configuration: Optional[dict] = None
    total_weight: Optional[int] = None
    criteria: List[CriterionResponse] = []
    jd_extraction_json: Optional[dict] = None
    created_at: datetime
    updated_at: datetime
    approved_at: Optional[datetime] = None

    @model_validator(mode="after")
    def sync_aliases(self) -> "ScorecardResponse":
        if self.version is None:
            self.version = self.version_number
        if self.scoring_configuration is None and self.scoring_config is not None:
            self.scoring_configuration = self.scoring_config
        return self

    model_config = {"from_attributes": True}


# ── JD extraction request ────────────────────────────────────────────────────

class ExtractRequirementsRequest(BaseModel):
    job_description: str = Field(..., min_length=10, max_length=50000)


# ── Requisition summary for recruiter workspace ──────────────────────────────

class RequisitionSummaryResponse(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    location: Optional[str] = None
    created_at: datetime
    candidate_count: int = 0
    evaluated_count: int = 0
    pending_reviews_count: int = 0
    shortlisted_count: int = 0
    rejected_count: int = 0
    hold_count: int = 0
    average_score: Optional[float] = None
    top_score: Optional[float] = None
    approved_scorecard_id: Optional[uuid.UUID] = None
    scorecard_version: Optional[int] = None

    model_config = {"from_attributes": True}

