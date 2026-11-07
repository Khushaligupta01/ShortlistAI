from __future__ import annotations

import asyncio
from typing import Any
import pytest
from pydantic import ValidationError

from app.ai.jd_extraction_service import JDExtractionService, _check_for_protected_attributes
from app.ai.provider import LLMExtractionError, LLMProviderUnavailableError
from app.ai.schemas import (
    ExperienceRequirement,
    ExtractionWarning,
    JDExtractionResult,
    NoticePeriodRequirement,
    SkillRequirement,
)


class MockLLMProvider:
    """Configurable mock provider for deterministic testing."""

    def __init__(
        self,
        response: dict[str, Any] | None = None,
        exc: Exception | None = None,
        delay: float = 0.0,
    ) -> None:
        self.response = response or {}
        self.exc = exc
        self.delay = delay
        self.call_count = 0
        self.last_prompt = ""

    async def extract_jd(
        self,
        prompt: str,
        output_schema: dict[str, Any],
        max_tokens: int,
    ) -> dict[str, Any]:
        self.call_count += 1
        self.last_prompt = prompt
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        if self.exc:
            raise self.exc
        return self.response


# ── AI Extraction Test Cases (1-14) ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_01_complete_job_description():
    """Test 1: Complete JD with all fields extracted cleanly."""
    mock_response = {
        "job_title": "Senior Java Developer",
        "department": "Engineering",
        "seniority_level": "Senior",
        "location": "Noida",
        "work_arrangement": "Hybrid",
        "employment_type": "Full-time",
        "summary": "Looking for an experienced Senior Java Developer.",
        "experience": {
            "minimum_years": 5,
            "maximum_years": 8,
            "evidence": "5-8 years of experience required",
            "is_explicit": True,
        },
        "must_have_skills": [
            {
                "name": "Java",
                "normalized_name": "java",
                "description": "Core Java expertise",
                "importance": "High",
                "evidence": "Strong Java development experience required",
                "is_mandatory": True,
            },
            {
                "name": "Spring Boot",
                "normalized_name": "spring_boot",
                "description": "Microservices with Spring",
                "importance": "High",
                "evidence": "Hands-on Spring Boot experience required",
                "is_mandatory": True,
            },
        ],
        "nice_to_have_skills": [
            {
                "name": "Microservices",
                "normalized_name": "microservices",
                "description": "Distributed architecture",
                "importance": "Medium",
                "evidence": "Microservices experience preferred",
                "is_mandatory": False,
            }
        ],
        "notice_period": {
            "maximum_days": 60,
            "original_wording": "Notice period up to 60 days",
            "is_explicit": True,
        },
        "additional_requirements": [
            {
                "category": "education",
                "description": "Bachelor's degree in Computer Science",
                "evidence": "B.Tech or equivalent required",
                "is_mandatory": True,
            }
        ],
        "extraction_warnings": [],
    }

    provider = MockLLMProvider(response=mock_response)
    service = JDExtractionService(provider)

    result = await service.extract("Some realistic job description text")
    assert result.job_title == "Senior Java Developer"
    assert result.location == "Noida"
    assert result.experience is not None
    assert result.experience.minimum_years == 5
    assert result.experience.maximum_years == 8
    assert len(result.must_have_skills) == 2
    assert result.must_have_skills[0].name == "Java"
    assert len(result.nice_to_have_skills) == 1
    assert result.notice_period is not None
    assert result.notice_period.maximum_days == 60


@pytest.mark.asyncio
async def test_02_missing_notice_period():
    """Test 2: When notice period is absent, maximum_days must be None (never 30 or 60)."""
    mock_response = {
        "job_title": "Java Developer",
        "location": "Noida",
        "experience": {"minimum_years": 3, "maximum_years": 5, "is_explicit": True},
        "must_have_skills": [{"name": "Java", "normalized_name": "java"}],
        "nice_to_have_skills": [],
        "notice_period": None,
        "additional_requirements": [],
        "extraction_warnings": [],
    }
    provider = MockLLMProvider(response=mock_response)
    service = JDExtractionService(provider)

    result = await service.extract("Job description with no notice period mentioned.")
    assert result.notice_period is None


@pytest.mark.asyncio
async def test_03_missing_location():
    """Test 3: When location is not specified in the JD, it remains None."""
    mock_response = {
        "job_title": "Backend Engineer",
        "location": None,
        "experience": {"minimum_years": 4, "maximum_years": None, "is_explicit": True},
        "must_have_skills": [{"name": "Python", "normalized_name": "python"}],
        "nice_to_have_skills": [],
        "notice_period": None,
        "additional_requirements": [],
        "extraction_warnings": [],
    }
    provider = MockLLMProvider(response=mock_response)
    service = JDExtractionService(provider)

    result = await service.extract("Job description without location.")
    assert result.location is None


@pytest.mark.asyncio
async def test_04_missing_experience():
    """Test 4: When experience is not specified, it remains None."""
    mock_response = {
        "job_title": "Junior Developer",
        "location": "Remote",
        "experience": None,
        "must_have_skills": [{"name": "Go", "normalized_name": "go"}],
        "nice_to_have_skills": [],
        "notice_period": None,
        "additional_requirements": [],
        "extraction_warnings": [],
    }
    provider = MockLLMProvider(response=mock_response)
    service = JDExtractionService(provider)

    result = await service.extract("Job description without experience requirement.")
    assert result.experience is None


@pytest.mark.asyncio
async def test_05_multiple_required_skills():
    """Test 5: Multiple must-have skills are correctly parsed, normalized, and deduplicated."""
    mock_response = {
        "job_title": "Full Stack Engineer",
        "must_have_skills": [
            {"name": "Java", "normalized_name": "java", "is_mandatory": True},
            {"name": "Spring Boot", "normalized_name": "spring-boot", "is_mandatory": True},
            {"name": "PostgreSQL", "normalized_name": "postgresql", "is_mandatory": True},
            {"name": "Java", "normalized_name": "java", "is_mandatory": True},  # Duplicate
        ],
        "nice_to_have_skills": [],
    }
    provider = MockLLMProvider(response=mock_response)
    service = JDExtractionService(provider)

    result = await service.extract("Job description with multiple skills.")
    # Duplicate skill should be deduplicated
    assert len(result.must_have_skills) == 3
    skill_names = [s.name for s in result.must_have_skills]
    assert "Java" in skill_names
    assert "Spring Boot" in skill_names
    assert "PostgreSQL" in skill_names


@pytest.mark.asyncio
async def test_06_nice_to_have_skills():
    """Test 6: Nice-to-have skills are properly segregated and marked non-mandatory."""
    mock_response = {
        "job_title": "DevOps Engineer",
        "must_have_skills": [{"name": "Linux", "normalized_name": "linux", "is_mandatory": True}],
        "nice_to_have_skills": [
            {
                "name": "Kubernetes",
                "normalized_name": "kubernetes",
                "evidence": "Kubernetes experience is a plus",
                "is_mandatory": False,
            },
            {
                "name": "Terraform",
                "normalized_name": "terraform",
                "evidence": "Terraform preferred",
                "is_mandatory": False,
            },
        ],
    }
    provider = MockLLMProvider(response=mock_response)
    service = JDExtractionService(provider)

    result = await service.extract("Job description with preferred skills.")
    assert len(result.nice_to_have_skills) == 2
    assert result.nice_to_have_skills[0].name == "Kubernetes"
    assert result.nice_to_have_skills[1].name == "Terraform"


@pytest.mark.asyncio
async def test_07_contradictory_requirements():
    """Test 7: Contradictory requirements in JD produce extraction warnings."""
    mock_response = {
        "job_title": "Lead Architect",
        "experience": {"minimum_years": 5, "maximum_years": 8, "is_explicit": True},
        "must_have_skills": [{"name": "Java", "normalized_name": "java"}],
        "extraction_warnings": [
            {
                "field": "experience",
                "message": "JD states '5-8 years' in summary but 'minimum 12 years' in requirements. Flagged for review.",
                "severity": "warning",
            }
        ],
    }
    provider = MockLLMProvider(response=mock_response)
    service = JDExtractionService(provider)

    result = await service.extract("Contradictory JD text")
    assert len(result.extraction_warnings) >= 1
    assert any("experience" in w.field for w in result.extraction_warnings)


@pytest.mark.asyncio
async def test_08_malformed_ai_json():
    """Test 8: Malformed JSON from AI provider raises LLMExtractionError."""
    provider = MockLLMProvider(exc=LLMExtractionError("Malformed JSON from AI provider: Expecting value", retryable=False))
    service = JDExtractionService(provider)

    with pytest.raises(LLMExtractionError) as exc_info:
        await service.extract("Any valid JD text")
    assert "Malformed JSON" in str(exc_info.value)


@pytest.mark.asyncio
async def test_09_invalid_experience_ranges():
    """Test 9: Invalid experience ranges (minimum > maximum) fail schema validation."""
    mock_response = {
        "job_title": "Developer",
        "experience": {
            "minimum_years": 10,
            "maximum_years": 5,  # Invalid: min > max
            "is_explicit": True,
        },
        "must_have_skills": [],
    }
    provider = MockLLMProvider(response=mock_response)
    service = JDExtractionService(provider)

    with pytest.raises(LLMExtractionError) as exc_info:
        await service.extract("Some JD text")
    assert "failed validation" in str(exc_info.value)


@pytest.mark.asyncio
async def test_10_ai_provider_timeout():
    """Test 10: Provider timeouts raise LLMExtractionError."""
    provider = MockLLMProvider(exc=LLMExtractionError("AI provider connection error: Request timed out", retryable=True))
    service = JDExtractionService(provider)

    with pytest.raises(LLMExtractionError) as exc_info:
        await service.extract("Some JD text")
    assert "timed out" in str(exc_info.value)


@pytest.mark.asyncio
async def test_11_ai_provider_unavailable():
    """Test 11: When AI provider is not configured, raises LLMProviderUnavailableError."""
    provider = MockLLMProvider(exc=LLMProviderUnavailableError("OpenAI provider is not configured. Set AI_API_KEY in environment."))
    service = JDExtractionService(provider)

    with pytest.raises(LLMProviderUnavailableError) as exc_info:
        await service.extract("Some JD text")
    assert "not configured" in str(exc_info.value)


@pytest.mark.asyncio
async def test_12_ai_rate_limit():
    """Test 12: Rate limit error raises LLMExtractionError with appropriate message."""
    provider = MockLLMProvider(exc=LLMExtractionError("AI provider rate limit reached: 429 Too Many Requests", retryable=True))
    service = JDExtractionService(provider)

    with pytest.raises(LLMExtractionError) as exc_info:
        await service.extract("Some JD text")
    assert "rate limit" in str(exc_info.value)


@pytest.mark.asyncio
async def test_13_protected_attributes_in_jd():
    """Test 13: Protected attributes in JD are flagged in extraction_warnings and excluded from criteria."""
    jd_with_pa = (
        "We are hiring a male Java developer, age 25-30, married candidates preferred. "
        "Must have 5 years Java experience."
    )
    warnings = _check_for_protected_attributes(jd_with_pa)
    assert len(warnings) > 0
    assert any("protected attributes" in w.message.lower() for w in warnings)

    # When passing through service, warnings are prepended
    mock_response = {
        "job_title": "Java Developer",
        "must_have_skills": [{"name": "Java", "normalized_name": "java"}],
        "extraction_warnings": [],
    }
    provider = MockLLMProvider(response=mock_response)
    service = JDExtractionService(provider)

    result = await service.extract(jd_with_pa)
    assert len(result.extraction_warnings) > 0
    # None of the protected attributes should be skills
    skill_names = [s.name.lower() for s in result.must_have_skills]
    assert "male" not in skill_names
    assert "married" not in skill_names


@pytest.mark.asyncio
async def test_14_very_long_job_description():
    """Test 14: Handles very long JDs (>10k chars) without crashing, truncating prompt safely."""
    long_jd = "Senior Python Developer required. " * 500  # ~17,000 chars
    mock_response = {
        "job_title": "Senior Python Developer",
        "must_have_skills": [{"name": "Python", "normalized_name": "python"}],
    }
    provider = MockLLMProvider(response=mock_response)
    service = JDExtractionService(provider)

    result = await service.extract(long_jd)
    assert result.job_title == "Senior Python Developer"
    # Verify the prompt sent to provider was capped at 8000 chars of JD
    assert len(provider.last_prompt) < 9000
