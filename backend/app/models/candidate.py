from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base, GUID

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.resume import Resume
    from app.models.evaluation import Evaluation
    from app.models.submission import Submission


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notice_period_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parsed_profile_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_anonymized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    organization: Mapped[Organization] = relationship("Organization")
    resumes: Mapped[list[Resume]] = relationship(
        "Resume", back_populates="candidate", lazy="select"
    )
    evaluations: Mapped[list[Evaluation]] = relationship(
        "Evaluation", back_populates="candidate", lazy="select"
    )
    submissions: Mapped[list[Submission]] = relationship(
        "Submission", back_populates="candidate", lazy="select"
    )

    __table_args__ = (
        Index("ix_candidates_org_id", "organization_id"),
        Index("ix_candidates_org_email", "organization_id", "email"),
    )
