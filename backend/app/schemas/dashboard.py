from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class DashboardMetricsResponse(BaseModel):
    active_requisitions: int
    total_candidates: int
    resumes_processed: int
    resumes_pending: int
    failed_jobs: int
    candidates_awaiting_review: int
    candidates_shortlisted: int
    completed_evaluations: int

    model_config = ConfigDict(from_attributes=True)


class RequisitionOverviewItem(BaseModel):
    id: str
    title: str
    department: Optional[str] = None
    location: Optional[str] = None
    status: str
    target_hire_date: Optional[str] = None
    candidate_count: int = 0
    evaluated_count: int = 0
    pending_reviews_count: int = 0
    shortlisted_count: int = 0
    average_score: Optional[float] = None
    top_score: Optional[float] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ProcessingOverviewResponse(BaseModel):
    total_uploaded: int
    total_processed: int
    total_pending: int
    total_failed: int
    success_rate_percent: float

    model_config = ConfigDict(from_attributes=True)


class DashboardActivityItem(BaseModel):
    id: str
    type: str  # requisition_created, batch_uploaded, evaluation_completed, review_recorded, note_added
    title: str
    description: str
    timestamp: datetime
    actor_name: Optional[str] = None
    entity_id: Optional[str] = None
    entity_type: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DashboardActivityResponse(BaseModel):
    activities: List[DashboardActivityItem]

    model_config = ConfigDict(from_attributes=True)


class RecruiterDashboardResponse(BaseModel):
    metrics: DashboardMetricsResponse
    requisitions: List[RequisitionOverviewItem]
    processing: ProcessingOverviewResponse
    recent_activity: List[DashboardActivityItem]

    model_config = ConfigDict(from_attributes=True)

