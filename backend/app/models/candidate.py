from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base, GUID

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.resume import Resume
    from app.models.evaluation import Evaluation
    from app.models.submission import Submission
    from app.models.candidate_note import CandidateNote


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
    total_experience_years: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    certifications: Mapped[list | None] = mapped_column(JSON, nullable=True)
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
    employments: Mapped[list[CandidateEmployment]] = relationship(
        "CandidateEmployment", back_populates="candidate", cascade="all, delete-orphan", lazy="select"
    )
    educations: Mapped[list[CandidateEducation]] = relationship(
        "CandidateEducation", back_populates="candidate", cascade="all, delete-orphan", lazy="select"
    )
    skills: Mapped[list[CandidateSkill]] = relationship(
        "CandidateSkill", back_populates="candidate", cascade="all, delete-orphan", lazy="select"
    )
    notes: Mapped[list[CandidateNote]] = relationship(
        "CandidateNote", back_populates="candidate", cascade="all, delete-orphan", lazy="select"
    )

    __table_args__ = (
        Index("ix_candidates_org_id", "organization_id"),
        Index("ix_candidates_org_email", "organization_id", "email"),
    )


class CandidateEmployment(Base):
    __tablename__ = "candidate_employments"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    job_title: Mapped[str] = mapped_column(String(255), nullable=False)
    start_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    end_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    technologies: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    candidate: Mapped[Candidate] = relationship("Candidate", back_populates="employments")

    __table_args__ = (
        Index("ix_cand_emp_candidate_id", "candidate_id"),
    )


class CandidateEducation(Base):
    __tablename__ = "candidate_educations"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    institution: Mapped[str] = mapped_column(String(255), nullable=False)
    qualification: Mapped[str | None] = mapped_column(String(255), nullable=True)
    field_of_study: Mapped[str | None] = mapped_column(String(255), nullable=True)
    graduation_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    candidate: Mapped[Candidate] = relationship("Candidate", back_populates="educations")

    __table_args__ = (
        Index("ix_cand_edu_candidate_id", "candidate_id"),
    )


class CandidateSkill(Base):
    __tablename__ = "candidate_skills"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_name: Mapped[str] = mapped_column(String(100), nullable=False)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    candidate: Mapped[Candidate] = relationship("Candidate", back_populates="skills")

    __table_args__ = (
        Index("ix_cand_skills_candidate_id", "candidate_id"),
        Index("ix_cand_skills_cand_name", "candidate_id", "name"),
    )
