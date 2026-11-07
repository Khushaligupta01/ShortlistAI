from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base, GUID

if TYPE_CHECKING:
    from app.models.candidate import Candidate


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
    total_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    score_breakdown_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    candidate: Mapped[Candidate] = relationship("Candidate", back_populates="evaluations")
    evidence: Mapped[list[EvaluationEvidence]] = relationship(
        "EvaluationEvidence", back_populates="evaluation", lazy="select"
    )

    __table_args__ = (
        Index("ix_evaluations_candidate_id", "candidate_id"),
        Index("ix_evaluations_requisition_id", "requisition_id"),
        Index("ix_evaluations_cand_req", "candidate_id", "requisition_id"),
        Index("ix_evaluations_cand_current", "candidate_id", "is_current"),
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
    source_excerpts_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    flags_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_overridden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    overridden_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    overridden_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    evaluation: Mapped[Evaluation] = relationship("Evaluation", back_populates="evidence")

    __table_args__ = (
        Index("ix_eval_evidence_evaluation_id", "evaluation_id"),
        Index("ix_eval_evidence_criterion_id", "scorecard_criterion_id"),
    )
