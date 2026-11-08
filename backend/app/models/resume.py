from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base, GUID

if TYPE_CHECKING:
    from app.models.candidate import Candidate


class UploadBatch(Base):
    __tablename__ = "upload_batches"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    recruiter_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    requisition_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("requisitions.id", ondelete="RESTRICT"), nullable=False
    )
    total_files: Mapped[int] = mapped_column(Integer, nullable=False)
    accepted_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rejected_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processing_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Legacy fields preserved for compatibility
    processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicates: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="processing")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    resumes: Mapped[list[Resume]] = relationship("Resume", back_populates="upload_batch")
    processing_jobs: Mapped[list[ResumeProcessingJob]] = relationship(
        "ResumeProcessingJob", back_populates="batch", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_upload_batches_org_id", "organization_id"),
        Index("ix_upload_batches_recruiter_id", "recruiter_id"),
        Index("ix_upload_batches_requisition_id", "requisition_id"),
    )


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("candidates.id", ondelete="SET NULL"), nullable=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    requisition_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("requisitions.id", ondelete="SET NULL"), nullable=True
    )
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")

    parse_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    parse_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message_safe: Mapped[str | None] = mapped_column(Text, nullable=True)

    upload_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("upload_batches.id", ondelete="SET NULL"), nullable=True
    )
    duplicate_of_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True
    )
    duplicate_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    duplicate_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    candidate: Mapped[Candidate | None] = relationship("Candidate", back_populates="resumes")
    upload_batch: Mapped[UploadBatch | None] = relationship(
        "UploadBatch", back_populates="resumes"
    )
    processing_jobs: Mapped[list[ResumeProcessingJob]] = relationship(
        "ResumeProcessingJob", back_populates="resume", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_resumes_candidate_id", "candidate_id"),
        Index("ix_resumes_upload_batch_id", "upload_batch_id"),
        Index("ix_resumes_file_hash", "file_hash"),
        Index("ix_resumes_requisition_id", "requisition_id"),
        Index("ix_resumes_org_status", "organization_id", "parse_status"),
        Index("ix_resumes_duplicate_of_id", "duplicate_of_id"),
    )


class ResumeProcessingJob(Base):
    __tablename__ = "resume_processing_jobs"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    resume_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )
    batch_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("upload_batches.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    lock_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    resume: Mapped[Resume] = relationship("Resume", back_populates="processing_jobs")
    batch: Mapped[UploadBatch] = relationship("UploadBatch", back_populates="processing_jobs")

    __table_args__ = (
        Index("ix_resume_jobs_status_created", "status", "created_at"),
        Index("ix_resume_jobs_batch_id", "batch_id"),
        Index("ix_resume_jobs_resume_id", "resume_id"),
        Index("ix_resume_jobs_lock_id", "lock_id"),
        Index("ix_resume_jobs_org_status", "organization_id", "status"),
    )
