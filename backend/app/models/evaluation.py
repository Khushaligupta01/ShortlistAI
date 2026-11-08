from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base, GUID

if TYPE_CHECKING:
    from app.models.candidate import Candidate
    from app.models.organization import Organization
    from app.models.requisition import Requisition
    from app.models.scorecard import Scorecard, ScorecardCriterion
    from app.models.user import User


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    requisition_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("requisitions.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    initiated_by: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    total_candidates: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    error_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    requisition: Mapped[Requisition] = relationship("Requisition")
    organization: Mapped[Organization] = relationship("Organization")
    initiator: Mapped[User] = relationship("User")
    evaluations: Mapped[List[Evaluation]] = relationship("Evaluation", back_populates="run")

    __table_args__ = (
        Index("ix_evaluation_runs_org_id", "organization_id"),
        Index("ix_evaluation_runs_req_id", "requisition_id"),
        Index("ix_evaluation_runs_status", "status"),
    )


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("candidates.id", ondelete="RESTRICT"), nullable=False
    )
    requisition_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("requisitions.id", ondelete="RESTRICT"), nullable=False
    )
    scorecard_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("scorecards.id", ondelete="RESTRICT"), nullable=False
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=True
    )
    evaluation_run_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("evaluation_runs.id", ondelete="SET NULL"), nullable=True
    )
    total_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0.0)
    raw_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0.0)
    normalized_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0.0)
    evidence_coverage: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0.0)
    confidence_level: Mapped[str] = mapped_column(String(30), nullable=False, default="HIGH")
    evaluation_status: Mapped[str] = mapped_column(String(30), nullable=False, default="COMPLETED")
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    scorecard_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    score_breakdown_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    model_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    candidate: Mapped[Candidate] = relationship("Candidate", back_populates="evaluations")
    requisition: Mapped[Requisition] = relationship("Requisition")
    scorecard: Mapped[Scorecard] = relationship("Scorecard")
    organization: Mapped[Optional[Organization]] = relationship("Organization")
    run: Mapped[Optional[EvaluationRun]] = relationship("EvaluationRun", back_populates="evaluations")
    evidence: Mapped[List[EvaluationEvidence]] = relationship(
        "EvaluationEvidence", back_populates="evaluation", cascade="all, delete-orphan", lazy="select"
    )
    reviews: Mapped[List[RecruiterReview]] = relationship(
        "RecruiterReview", back_populates="evaluation", cascade="all, delete-orphan", lazy="select"
    )

    __table_args__ = (
        Index("ix_evaluations_candidate_id", "candidate_id"),
        Index("ix_evaluations_requisition_id", "requisition_id"),
        Index("ix_evaluations_cand_req", "candidate_id", "requisition_id"),
        Index("ix_evaluations_cand_current", "candidate_id", "is_current"),
        Index("ix_evaluations_org_id", "organization_id"),
        Index("ix_evaluations_status", "evaluation_status"),
        Index("ix_evaluations_run_id", "evaluation_run_id"),
    )


class EvaluationEvidence(Base):
    __tablename__ = "evaluation_evidence"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    evaluation_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False
    )
    scorecard_criterion_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("scorecard_criteria.id", ondelete="RESTRICT"), nullable=False
    )
    evidence_status: Mapped[str] = mapped_column(String(30), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    awarded_points: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0.0)
    maximum_points: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0.0)
    evidence_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_excerpts_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    flags_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_overridden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    overridden_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    overridden_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    evaluation: Mapped[Evaluation] = relationship("Evaluation", back_populates="evidence")
    criterion: Mapped[ScorecardCriterion] = relationship("ScorecardCriterion")

    __table_args__ = (
        Index("ix_eval_evidence_evaluation_id", "evaluation_id"),
        Index("ix_eval_evidence_criterion_id", "scorecard_criterion_id"),
    )


class RecruiterReview(Base):
    __tablename__ = "recruiter_reviews"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    evaluation_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False
    )
    recruiter_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    decision: Mapped[str] = mapped_column(String(30), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    evaluation: Mapped[Evaluation] = relationship("Evaluation", back_populates="reviews")
    recruiter: Mapped[User] = relationship("User")
    organization: Mapped[Organization] = relationship("Organization")

    __table_args__ = (
        Index("ix_recruiter_reviews_eval_id", "evaluation_id"),
        Index("ix_recruiter_reviews_org_id", "organization_id"),
    )
