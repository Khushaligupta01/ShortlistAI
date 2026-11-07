from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base, GUID

if TYPE_CHECKING:
    from app.models.requisition import Requisition


class Scorecard(Base):
    __tablename__ = "scorecards"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    requisition_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("requisitions.id", ondelete="RESTRICT"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    # Phase 3: structured fields on scorecard
    experience_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    experience_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    max_notice_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Scoring configuration: {experience: 30, must_have_skills: 40, notice_period: 15, location: 10, nice_to_have_skills: 5}
    scoring_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    total_weight: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    jd_extraction_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    requisition: Mapped[Requisition] = relationship("Requisition", back_populates="scorecards")
    criteria: Mapped[list[ScorecardCriterion]] = relationship(
        "ScorecardCriterion", back_populates="scorecard", lazy="select",
        order_by="ScorecardCriterion.display_order",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("requisition_id", "version_number", name="uq_scorecard_req_version"),
        Index("ix_scorecards_requisition_id", "requisition_id"),
        Index("ix_scorecards_req_status", "requisition_id", "status"),
    )


class ScorecardCriterion(Base):
    __tablename__ = "scorecard_criteria"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    scorecard_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("scorecards.id", ondelete="CASCADE"), nullable=False
    )
    criterion_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # Phase 3: richer criterion fields
    criterion_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    weight: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    evidence_from_jd: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    config_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    scorecard: Mapped[Scorecard] = relationship("Scorecard", back_populates="criteria")

    __table_args__ = (
        Index("ix_scorecard_criteria_scorecard_id", "scorecard_id"),
    )
