from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CriterionEvidenceResponse(BaseModel):
    id: str
    scorecard_criterion_id: str
    criterion_name: Optional[str] = None
    criterion_type: Optional[str] = None
    evidence_status: str
    confidence_score: float
    awarded_points: float
    maximum_points: float
    evidence_text: Optional[str] = None
    source_reference: Optional[str] = None
    explanation: Optional[str] = None
    is_overridden: bool = False
    override_reason: Optional[str] = None
    created_at: datetime


class RecruiterReviewRequest(BaseModel):
    decision: str = Field(..., description="SHORTLIST, REJECT, HOLD, or REQUEST_INFO")
    notes: Optional[str] = Field(None, max_length=2000)


class RecruiterReviewResponse(BaseModel):
    id: str
    evaluation_id: str
    recruiter_id: str
    decision: str
    notes: Optional[str] = None
    reviewed_at: datetime


class EvaluationResponse(BaseModel):
    id: str
    candidate_id: str
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
    candidate_location: Optional[str] = None
    candidate_experience_years: Optional[float] = None
    candidate_notice_days: Optional[int] = None
    candidate_skills: List[str] = Field(default_factory=list)
    requisition_id: str
    scorecard_id: str
    scorecard_version: int
    version_number: int
    total_score: float
    raw_score: float
    normalized_score: float
    evidence_coverage: float
    confidence_level: str
    evaluation_status: str
    is_current: bool
    score_breakdown: Dict[str, Any] = Field(default_factory=dict)
    evidence: Optional[List[CriterionEvidenceResponse]] = None
    reviews: Optional[List[RecruiterReviewResponse]] = None
    latest_review_decision: Optional[str] = None
    evaluated_at: Optional[datetime] = None
    created_at: datetime


class EvaluationListResponse(BaseModel):
    items: List[EvaluationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class EvaluationRunResponse(BaseModel):
    id: str
    requisition_id: str
    total_candidates: int
    completed_count: int
    failed_count: int
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_summary: Optional[Dict[str, Any]] = None


class BatchEvaluationRequest(BaseModel):
    candidate_ids: Optional[List[uuid.UUID]] = Field(
        None, description="Optional list of specific candidate UUIDs to evaluate"
    )

