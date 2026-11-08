from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------

class SubmissionCreateRequest(BaseModel):
    candidate_id: uuid.UUID
    client_organization_id: uuid.UUID
    recruiter_notes_for_client: Optional[str] = None


class ClientDecisionCreateRequest(BaseModel):
    decision: str = Field(..., description="CLIENT_SHORTLISTED, CLIENT_REJECTED, INTERVIEW_REQUESTED, ADDITIONAL_INFO_REQUESTED")
    reason_note: Optional[str] = None
    interview_details: Optional[str] = None
    info_request_details: Optional[str] = None


class ClientRequestCreateRequest(BaseModel):
    request_type: str = Field("ADDITIONAL_INFO", description="INTERVIEW or ADDITIONAL_INFO")
    details: str = Field(..., min_length=1)


class RecruiterResponseRequest(BaseModel):
    recruiter_response: str = Field(..., min_length=1)
    new_stage: Optional[str] = None


class RecruiterStageUpdateRequest(BaseModel):
    stage: str
    reason_note: Optional[str] = None


# ---------------------------------------------------------------------------
# Component & Nested Schemas
# ---------------------------------------------------------------------------

class PipelineRecordResponse(BaseModel):
    id: uuid.UUID
    submission_id: uuid.UUID
    current_stage: str
    previous_stage: Optional[str] = None
    changed_by: uuid.UUID
    actor_name: Optional[str] = None
    reason_note: Optional[str] = None
    changed_at: datetime
    is_reopened: bool = False

    class Config:
        from_attributes = True


class ClientRequestResponse(BaseModel):
    id: uuid.UUID
    submission_id: uuid.UUID
    client_organization_id: uuid.UUID
    requested_by: uuid.UUID
    requester_name: Optional[str] = None
    request_type: str
    details: str
    status: str
    recruiter_response: Optional[str] = None
    responded_by: Optional[uuid.UUID] = None
    responder_name: Optional[str] = None
    responded_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MaskedCriterionEvidence(BaseModel):
    criterion_id: uuid.UUID
    criterion_name: str
    category: str
    status: str
    evidence_excerpt: Optional[str] = None
    reasoning: Optional[str] = None


class MaskedEmployment(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: bool = False
    description: Optional[str] = None


class MaskedEducation(BaseModel):
    degree: Optional[str] = None
    institution: Optional[str] = None
    field_of_study: Optional[str] = None
    graduation_year: Optional[int] = None


class MaskedCandidateProfileResponse(BaseModel):
    submission_id: uuid.UUID
    candidate_id: uuid.UUID
    candidate_reference: str
    requisition_id: uuid.UUID
    requisition_title: str
    current_stage: str
    submitted_at: datetime
    recruiter_notes_for_client: Optional[str] = None
    location: Optional[str] = None
    total_experience_years: Optional[float] = None
    notice_period_days: Optional[int] = None
    overall_score: Optional[float] = None
    evaluation_summary: Optional[str] = None
    skills: list[str] = Field(default_factory=list)
    employments: list[MaskedEmployment] = Field(default_factory=list)
    educations: list[MaskedEducation] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    criterion_evaluations: list[MaskedCriterionEvidence] = Field(default_factory=list)
    latest_decision: Optional[str] = None
    pipeline_history: list[PipelineRecordResponse] = Field(default_factory=list)
    requests: list[ClientRequestResponse] = Field(default_factory=list)


class ClientSubmissionListItemResponse(BaseModel):
    submission_id: uuid.UUID
    candidate_id: uuid.UUID
    candidate_reference: str
    requisition_id: uuid.UUID
    requisition_title: str
    location: Optional[str] = None
    total_experience_years: Optional[float] = None
    overall_score: Optional[float] = None
    skills: list[str] = Field(default_factory=list)
    current_stage: str
    submitted_at: datetime
    pending_action: Optional[str] = None


class RecruiterSubmissionListItemResponse(BaseModel):
    submission_id: uuid.UUID
    candidate_id: uuid.UUID
    candidate_name: str
    candidate_email: str
    candidate_reference: str
    requisition_id: uuid.UUID
    requisition_title: str
    client_organization_id: uuid.UUID
    client_organization_name: str
    current_stage: str
    overall_score: Optional[float] = None
    submitted_at: datetime
    last_activity_at: datetime
    pending_requests_count: int = 0


class ClientDashboardMetricsResponse(BaseModel):
    active_requisitions_count: int = 0
    total_submissions_count: int = 0
    awaiting_review_count: int = 0
    shortlisted_count: int = 0
    rejected_count: int = 0
    interview_requested_count: int = 0
    additional_info_requested_count: int = 0


class PipelineStageSummaryResponse(BaseModel):
    stage: str
    stage_label: str
    count: int


class PipelineBoardResponse(BaseModel):
    stages: list[PipelineStageSummaryResponse]
    submissions: list[RecruiterSubmissionListItemResponse]


class ClientRequisitionListItemResponse(BaseModel):
    id: uuid.UUID
    title: str
    location: Optional[str] = None
    status: str
    created_at: datetime
    submissions_count: int = 0
    awaiting_review_count: int = 0


class ClientRequisitionDetailResponse(BaseModel):
    id: uuid.UUID
    title: str
    job_description: str
    location: Optional[str] = None
    status: str
    created_at: datetime
    submissions_count: int = 0

