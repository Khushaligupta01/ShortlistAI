from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
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
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
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
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    jd_extraction_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    requisition: Mapped[Requisition] = relationship("Requisition", back_populates="scorecards")
    criteria: Mapped[list[ScorecardCriterion]] = relationship(
        "ScorecardCriterion", back_populates="scorecard", lazy="select"
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
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    weight: Mapped[int] = mapped_column(Integer, nullable=False)
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
