from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID

if TYPE_CHECKING:
    from app.models.candidate import Candidate
    from app.models.organization import Organization
    from app.models.requisition import Requisition
    from app.models.user import User


class CandidateNote(Base):
    """
    Recruiter-only internal notes for candidates and requisitions.
    Strictly isolated to organization members; never exposed to client users.
    """
    __tablename__ = "candidate_notes"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    requisition_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("requisitions.id", ondelete="SET NULL"), nullable=True
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    candidate: Mapped[Candidate] = relationship("Candidate", back_populates="notes")
    requisition: Mapped[Requisition | None] = relationship("Requisition")
    author: Mapped[User] = relationship("User")
    organization: Mapped[Organization] = relationship("Organization")

    __table_args__ = (
        Index("ix_candidate_notes_candidate_id", "candidate_id"),
        Index("ix_candidate_notes_org_id", "organization_id"),
        Index("ix_candidate_notes_author_id", "author_id"),
        Index("ix_candidate_notes_requisition_id", "requisition_id"),
    )

