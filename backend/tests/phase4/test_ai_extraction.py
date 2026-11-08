from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from app.ai.provider import LLMExtractionError, LLMProviderUnavailableError
from app.ai.resume_extraction_service import ResumeExtractionService
from app.ai.schemas import ResumeExtractionResult


class MockProvider:
    def __init__(self, return_val: dict[str, Any] | Exception) -> None:
        self.return_val = return_val

    async def extract_jd(self, prompt: str, output_schema: dict, max_tokens: int):
        pass

    async def extract_resume(self, prompt: str, output_schema: dict, max_tokens: int) -> dict[str, Any]:
        if isinstance(self.return_val, Exception):
            raise self.return_val
        return self.return_val


@pytest.mark.asyncio
async def test_ai_extraction_valid_output():
    mock_payload = {
        "full_name": "Aarav Sharma",
        "email": "aarav.sharma@example.com",
        "phone": "+1-555-0101",
        "location": "San Jose, CA",
        "notice_period_days": 30,
        "total_experience_years": 8.0,
        "skills": [
            {"name": "java", "raw_name": "Java", "evidence": "Senior Java Engineer"},
            {"name": "spring boot", "raw_name": "Spring Boot", "evidence": "12 Spring Boot microservices"},
        ],
        "employment_history": [
            {
                "company": "Apex Tech Solutions",
                "job_title": "Senior Java Engineer",
                "start_date": "2020-01",
                "end_date": "Present",
                "is_current": True,
                "description": "Architected Spring Boot microservices",
                "technologies": ["Java", "Spring Boot", "Kafka"],
            }
        ],
        "education": [
            {
                "institution": "Stanford University",
                "qualification": "B.S. Computer Science",
                "field_of_study": "Computer Science",
                "graduation_year": 2016,
            }
        ],
        "certifications": [],
        "warnings": [],
        "missing_fields": [],
    }

    service = ResumeExtractionService(provider=MockProvider(mock_payload))
    result = await service.extract_candidate_profile("Sample text")

    assert isinstance(result, ResumeExtractionResult)
    assert result.full_name == "Aarav Sharma"
    assert result.email == "aarav.sharma@example.com"
    assert result.notice_period_days == 30
    assert len(result.skills) == 2
    assert len(result.employment_history) == 1
    assert result.education[0].institution == "Stanford University"


@pytest.mark.asyncio
async def test_ai_extraction_missing_fields_preserved_as_null():
    mock_payload = {
        "full_name": "Anonymous Candidate",
        "email": None,
        "phone": None,
        "location": None,
        "notice_period_days": None,
        "total_experience_years": None,
        "skills": [],
        "employment_history": [],
        "education": [],
        "certifications": [],
        "warnings": ["Notice period not stated"],
        "missing_fields": [],
    }

    service = ResumeExtractionService(provider=MockProvider(mock_payload))
    result = await service.extract_candidate_profile("Sample text")

    assert result.email is None
    assert result.phone is None
    assert result.notice_period_days is None
    assert "notice_period_days" in result.missing_fields
    assert "email" in result.missing_fields


@pytest.mark.asyncio
async def test_ai_extraction_provider_error_fallback():
    # If LLM raises error, fallback to deterministic parser
    resume_text = """
    Jane Doe
    jane.doe@example.com | 555-123-4567
    Notice period: 15 days
    Skills: Java, Python, Docker
    B.Tech Computer Science 2021
    """
    service = ResumeExtractionService(provider=MockProvider(LLMExtractionError("Rate limit", retryable=False)))
    result = await service.extract_candidate_profile(resume_text)

    assert result.email == "jane.doe@example.com"
    assert result.notice_period_days == 15
    assert any(s.raw_name == "Java" for s in result.skills)
    assert any("AI extraction unavailable" in w for w in result.warnings)


@pytest.mark.asyncio
async def test_ai_extraction_unavailable_provider():
    resume_text = "Bob Smith | bob.smith@example.com | Skills: React, TypeScript"
    service = ResumeExtractionService(provider=MockProvider(LLMProviderUnavailableError()))
    result = await service.extract_candidate_profile(resume_text)

    assert result.email == "bob.smith@example.com"
    assert any("rule-based" in w.lower() for w in result.warnings)
