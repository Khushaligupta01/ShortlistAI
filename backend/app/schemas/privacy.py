from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# Candidate Consent Schemas
# ============================================================================

class ConsentRequestCreate(BaseModel):
    purpose: str = Field(
        default="resume_screening_and_shortlisting",
        description="Purpose for processing candidate personal data"
    )
    collection_method: str = Field(
        default="PUBLIC_LINK",
        description="Method used: PUBLIC_LINK, DIRECT_NOTICE, or VERBAL_RECORDED"
    )
    requisition_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Optional requisition context"
    )


class ConsentRequestResponse(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    status: str
    purpose: str
    version: str
    collection_method: str
    token: Optional[str] = None
    consent_url: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    created_at: datetime


class ConsentRecordResponse(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    organization_id: uuid.UUID
    uploaded_by: uuid.UUID
    legal_basis: str
    status: str
    purpose: str
    version: str
    collection_method: str
    requisition_id: Optional[uuid.UUID] = None
    privacy_notice_acknowledged: bool
    withdrawn_at: Optional[datetime] = None
    withdrawal_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ConsentPublicInfoResponse(BaseModel):
    token: str
    candidate_reference: str
    organization_name: str
    purpose: str
    version: str
    token_expires_at: Optional[datetime] = None
    status: str
    is_valid: bool


class ConsentDecisionRequest(BaseModel):
    decision: str = Field(
        ...,
        description="Candidate consent decision: GRANTED or DECLINED"
    )
    reason: Optional[str] = Field(
        default=None,
        description="Optional reason provided by candidate"
    )


class ConsentWithdrawRequest(BaseModel):
    reason: Optional[str] = Field(
        default=None,
        description="Reason for withdrawing consent"
    )


# ============================================================================
# Candidate Data Access & Export Schemas
# ============================================================================

class DataRequestCreate(BaseModel):
    request_type: str = Field(
        default="EXPORT",
        description="ACCESS or EXPORT"
    )
    reason: Optional[str] = Field(
        default=None,
        description="Optional justification for data access/export request"
    )


class DataRequestResponse(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    organization_id: uuid.UUID
    requested_by: uuid.UUID
    request_type: str
    status: str
    export_file_path: Optional[str] = None
    export_metadata: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class CandidateExportData(BaseModel):
    export_id: uuid.UUID
    exported_at: datetime
    candidate_id: uuid.UUID
    organization_id: uuid.UUID
    profile: Dict[str, Any]
    employments: List[Dict[str, Any]]
    educations: List[Dict[str, Any]]
    skills: List[Dict[str, Any]]
    resumes: List[Dict[str, Any]]
    evaluations: List[Dict[str, Any]]
    recruiter_reviews: List[Dict[str, Any]]
    submissions: List[Dict[str, Any]]
    consent_history: List[Dict[str, Any]]
    processing_status: Dict[str, Any]
    excluded_fields_notice: str


# ============================================================================
# Candidate Deletion Request Schemas
# ============================================================================

class DeletionRequestCreate(BaseModel):
    reason: Optional[str] = Field(
        default=None,
        description="Reason for deletion request (e.g. candidate request, retention limit)"
    )


class DeletionReviewRequest(BaseModel):
    decision: str = Field(
        ...,
        description="APPROVE or REJECT"
    )
    review_notes: Optional[str] = Field(
        default=None,
        description="Reviewer notes justifying the decision"
    )
    retention_policy_notes: Optional[str] = Field(
        default=None,
        description="Notes citing organizational retention policy or legal hold"
    )
    is_legal_hold: bool = Field(
        default=False,
        description="Whether a legal hold prevents deletion"
    )
    legal_hold_reason: Optional[str] = Field(
        default=None,
        description="Reason for active legal hold"
    )


class DeletionRequestResponse(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    organization_id: uuid.UUID
    requested_by: uuid.UUID
    reviewer_id: Optional[uuid.UUID] = None
    reason: Optional[str] = None
    status: str
    review_decision: Optional[str] = None
    review_notes: Optional[str] = None
    retention_policy_notes: Optional[str] = None
    files_deleted_count: int
    is_legal_hold: bool
    legal_hold_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


class DeletionExecuteResponse(BaseModel):
    deletion_request_id: uuid.UUID
    candidate_id: uuid.UUID
    status: str
    files_deleted_count: int
    anonymized: bool
    completed_at: datetime
    message: str


# ============================================================================
# Audit Log Schemas
# ============================================================================

class AuditEventResponse(BaseModel):
    id: uuid.UUID
    organization_id: Optional[uuid.UUID] = None
    actor_user_id: Optional[uuid.UUID] = None
    actor_name: Optional[str] = None
    event_type: str
    resource_type: Optional[str] = None
    resource_id: Optional[uuid.UUID] = None
    payload_json: Optional[Dict[str, Any]] = None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: List[AuditEventResponse]
    total: int
    page: int
    page_size: int


# ============================================================================
# Responsible AI Governance Schemas
# ============================================================================

class GovernanceAIMetricsResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    total_evaluations: int
    score_distribution: Dict[str, int]
    average_score: float
    average_evidence_coverage_pct: float
    unknown_criteria_frequency: Dict[str, int]
    recruiter_review_distribution: Dict[str, int]
    override_rate_pct: float
    model_breakdown: Dict[str, int]
    fairness_and_bias_disclaimer: str


class EvaluationQualityResponse(BaseModel):
    total_evaluations: int
    confidence_breakdown: Dict[str, int]
    token_verification_pass_rate_pct: float
    scanned_image_ocr_rate_pct: float
    processing_error_rate_pct: float
    quality_assurance_notes: List[str]


# ============================================================================
# Privacy Dashboard Schemas
# ============================================================================

class PrivacyDashboardResponse(BaseModel):
    pending_consent_requests_count: int
    granted_consents_count: int
    withdrawn_consents_count: int
    pending_data_requests_count: int
    completed_exports_count: int
    pending_deletion_requests_count: int
    completed_deletions_count: int
    active_legal_holds_count: int
    recent_audit_events: List[AuditEventResponse]
