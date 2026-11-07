"""
Strict Pydantic schemas for AI extraction outputs.

All AI output is validated against these schemas before
reaching the database or frontend.
"""
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Sub-schemas
# ---------------------------------------------------------------------------

class ExperienceRequirement(BaseModel):
    minimum_years: Optional[int] = Field(None, ge=0, le=50)
    maximum_years: Optional[int] = Field(None, ge=0, le=60)
    evidence: Optional[str] = Field(None, max_length=500)
    is_explicit: bool = Field(default=False)

    @model_validator(mode="after")
    def validate_range(self) -> "ExperienceRequirement":
        if (
            self.minimum_years is not None
            and self.maximum_years is not None
            and self.minimum_years > self.maximum_years
        ):
            raise ValueError(
                f"minimum_years ({self.minimum_years}) cannot exceed "
                f"maximum_years ({self.maximum_years})"
            )
        return self


class SkillRequirement(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    normalized_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    importance: Optional[str] = Field(None, max_length=50)
    evidence: Optional[str] = Field(None, max_length=500)
    is_mandatory: bool = Field(default=True)

    @field_validator("normalized_name", mode="before")
    @classmethod
    def normalize(cls, v: str) -> str:
        return v.strip().lower().replace(" ", "_").replace("-", "_")

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()


class NoticePeriodRequirement(BaseModel):
    maximum_days: Optional[int] = Field(None, ge=0, le=365)
    original_wording: Optional[str] = Field(None, max_length=200)
    is_explicit: bool = Field(default=False)


class AdditionalRequirement(BaseModel):
    category: str = Field(..., max_length=50)  # e.g. "education", "certification"
    description: str = Field(..., min_length=1, max_length=500)
    evidence: Optional[str] = Field(None, max_length=500)
    is_mandatory: bool = Field(default=False)


class ExtractionWarning(BaseModel):
    field: str = Field(..., max_length=100)
    message: str = Field(..., max_length=500)
    severity: Literal["info", "warning", "error"] = "warning"


# ---------------------------------------------------------------------------
# Main extraction result
# ---------------------------------------------------------------------------

class JDExtractionResult(BaseModel):
    """
    Validated structured output of JD extraction.
    Every field that cannot be extracted from the JD is null.
    No fabrication — null means not stated in the JD.
    """
    job_title: Optional[str] = Field(None, max_length=255)
    department: Optional[str] = Field(None, max_length=100)
    seniority_level: Optional[str] = Field(None, max_length=50)
    location: Optional[str] = Field(None, max_length=255)
    work_arrangement: Optional[str] = Field(None, max_length=50)
    employment_type: Optional[str] = Field(None, max_length=50)
    summary: Optional[str] = Field(None, max_length=1000)

    experience: Optional[ExperienceRequirement] = None
    must_have_skills: list[SkillRequirement] = Field(default_factory=list, max_length=30)
    nice_to_have_skills: list[SkillRequirement] = Field(default_factory=list, max_length=20)
    notice_period: Optional[NoticePeriodRequirement] = None
    additional_requirements: list[AdditionalRequirement] = Field(
        default_factory=list, max_length=20
    )
    extraction_warnings: list[ExtractionWarning] = Field(default_factory=list, max_length=20)

    @field_validator("must_have_skills", "nice_to_have_skills", mode="after")
    @classmethod
    def deduplicate_skills(cls, skills: list[SkillRequirement]) -> list[SkillRequirement]:
        seen: set[str] = set()
        unique = []
        for skill in skills:
            key = skill.normalized_name
            if key not in seen:
                seen.add(key)
                unique.append(skill)
        return unique


# ---------------------------------------------------------------------------
# Scoring configuration
# ---------------------------------------------------------------------------

DEFAULT_SCORING_CONFIG = {
    "experience": 30,
    "must_have_skills": 40,
    "notice_period": 15,
    "location": 10,
    "nice_to_have_skills": 5,
}


class ScoringConfig(BaseModel):
    experience: int = Field(30, ge=0, le=100)
    must_have_skills: int = Field(40, ge=0, le=100)
    notice_period: int = Field(15, ge=0, le=100)
    location: int = Field(10, ge=0, le=100)
    nice_to_have_skills: int = Field(5, ge=0, le=100)

    @model_validator(mode="after")
    def validate_total(self) -> "ScoringConfig":
        total = (
            self.experience
            + self.must_have_skills
            + self.notice_period
            + self.location
            + self.nice_to_have_skills
        )
        if total != 100:
            raise ValueError(f"Scoring weights must sum to 100, got {total}")
        return self
