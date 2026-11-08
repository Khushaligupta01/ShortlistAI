from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID

if TYPE_CHECKING:
    from app.models.candidate import Candidate
    from app.models.evaluation import Evaluation
    from app.models.organization import Organization
    from app.models.requisition import Requisition
    from app.models.user import User


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("candidates.id", ondelete="RESTRICT"), nullable=False
    )
    requisition_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("requisitions.id", ondelete="RESTRICT"), nullable=False
    )
    evaluation_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("evaluations.id", ondelete="RESTRICT"), nullable=False
    )
    submitted_by: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    source_organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    client_organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    current_stage: Mapped[str] = mapped_column(String(50), nullable=False, default="SUBMITTED")
    recruiter_notes_for_client: Mapped[str | None] = mapped_column(Text, nullable=True)
    custom_candidate_reference: Mapped[str | None] = mapped_column(String(50), nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    candidate: Mapped[Candidate] = relationship("Candidate", back_populates="submissions")
    requisition: Mapped[Requisition] = relationship("Requisition", back_populates="submissions")
    evaluation: Mapped[Evaluation] = relationship("Evaluation")
    submitter: Mapped[User] = relationship("User", foreign_keys=[submitted_by])
    source_organization: Mapped[Organization] = relationship("Organization", foreign_keys=[source_organization_id])
    client_organization: Mapped[Organization] = relationship("Organization", foreign_keys=[client_organization_id])
    pipeline_records: Mapped[list[PipelineRecord]] = relationship(
        "PipelineRecord", back_populates="submission", lazy="select", cascade="all, delete-orphan"
    )
    requests: Mapped[list[ClientRequest]] = relationship(
        "ClientRequest", back_populates="submission", lazy="select", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_submissions_candidate_id", "candidate_id"),
        Index("ix_submissions_requisition_id", "requisition_id"),
        Index("ix_submissions_client_org_id", "client_organization_id"),
        Index("ix_submissions_client_org_status", "client_organization_id", "status"),
        Index("ix_submissions_current_stage", "current_stage"),
    )


class PipelineRecord(Base):
    __tablename__ = "pipeline_records"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False
    )
    current_stage: Mapped[str] = mapped_column(String(50), nullable=False)
    previous_stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    changed_by: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    reason_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    is_reopened: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    submission: Mapped[Submission] = relationship("Submission", back_populates="pipeline_records")
    changer: Mapped[User] = relationship("User", foreign_keys=[changed_by])

    __table_args__ = (
        Index("ix_pipeline_records_submission_id", "submission_id"),
        Index("ix_pipeline_records_changed_at", "changed_at"),
    )


class ClientRequest(Base):
    __tablename__ = "client_requests"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False
    )
    client_organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    request_type: Mapped[str] = mapped_column(String(50), nullable=False)  # INTERVIEW, ADDITIONAL_INFO
    details: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")  # PENDING, RESPONDED, CLOSED
    recruiter_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    responded_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    submission: Mapped[Submission] = relationship("Submission", back_populates="requests")
    requester: Mapped[User] = relationship("User", foreign_keys=[requested_by])
    responder: Mapped[User | None] = relationship("User", foreign_keys=[responded_by])
    client_organization: Mapped[Organization] = relationship("Organization", foreign_keys=[client_organization_id])

    __table_args__ = (
        Index("ix_client_requests_submission_id", "submission_id"),
        Index("ix_client_requests_client_org_id", "client_organization_id"),
        Index("ix_client_requests_status", "status"),
    )
