from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User
    from app.models.scorecard import Scorecard
    from app.models.submission import Submission


class Requisition(Base):
    __tablename__ = "requisitions"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    job_description: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    client_organization_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    organization: Mapped[Organization] = relationship(
        "Organization", back_populates="requisitions", foreign_keys=[organization_id]
    )
    creator: Mapped[User] = relationship("User", foreign_keys=[created_by])
    client_organization: Mapped[Organization | None] = relationship(
        "Organization", foreign_keys=[client_organization_id]
    )
    scorecards: Mapped[list[Scorecard]] = relationship(
        "Scorecard", back_populates="requisition", lazy="select"
    )
    submissions: Mapped[list[Submission]] = relationship(
        "Submission", back_populates="requisition", lazy="select"
    )

    __table_args__ = (
        Index("ix_requisitions_org_id", "organization_id"),
        Index("ix_requisitions_status", "status"),
        Index("ix_requisitions_org_status", "organization_id", "status"),
        Index("ix_requisitions_client_org_id", "client_organization_id"),
    )
