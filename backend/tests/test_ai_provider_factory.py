"""
Focused test suite for AI provider selection, configuration validation,
and test-mode mock provider behavior.
"""
from __future__ import annotations

import pytest

from app.ai.mock_provider import MockLLMProvider
from app.ai.openai_provider import OpenAIProvider
from app.ai.provider_factory import get_llm_provider, get_provider, reset_provider
from app.core.config import Settings


def test_provider_selection_openai():
    """Verify 'openai' provider selection loads OpenAIProvider."""
    config = Settings(AI_PROVIDER="openai", AI_API_KEY="test-fake-key", APP_ENV="development")
    provider = get_llm_provider(config)
    assert isinstance(provider, OpenAIProvider)
    assert provider._model == "gpt-4o-mini"


def test_provider_selection_mock_and_fallback():
    """Verify 'mock', 'fallback', and 'test' load MockLLMProvider in development/test."""
    for variant in ["mock", "fallback", "test", "MOCK", "Fallback"]:
        config = Settings(AI_PROVIDER=variant, APP_ENV="development")
        provider = get_llm_provider(config)
        assert isinstance(provider, MockLLMProvider)
        assert provider.name == "mock"


def test_invalid_provider_raises_actionable_error():
    """Verify unsupported provider names raise descriptive ValueError."""
    config = Settings(AI_PROVIDER="unsupported_vendor", APP_ENV="development")
    with pytest.raises(ValueError) as exc_info:
        get_llm_provider(config)
    assert "Unknown AI_PROVIDER 'unsupported_vendor'" in str(exc_info.value)
    assert "openai" in str(exc_info.value)


def test_mock_provider_strictly_forbidden_in_production():
    """Verify mock/fallback providers are rejected in production environment."""
    for variant in ["mock", "fallback", "test"]:
        config = Settings(AI_PROVIDER=variant, APP_ENV="production", JWT_SECRET_KEY="a"*32)
        with pytest.raises(ValueError) as exc_info:
            get_llm_provider(config)
        assert "not permitted in production" in str(exc_info.value)


def test_provider_factory_string_argument():
    """Verify get_llm_provider accepts plain string provider names."""
    provider = get_llm_provider("fallback")
    assert isinstance(provider, MockLLMProvider)


@pytest.mark.asyncio
async def test_mock_provider_extract_jd_structural_validity():
    """Verify MockLLMProvider.extract_jd returns valid schema-compliant dictionary."""
    provider = MockLLMProvider()
    jd_prompt = "Looking for a Senior Backend Engineer with 5+ years of experience in Python and FastAPI. Remote. 30 days notice."
    result = await provider.extract_jd(jd_prompt, output_schema={}, max_tokens=1000)

    assert isinstance(result, dict)
    assert result["job_title"] in ("Senior Backend Engineer", "Software Engineer")
    assert result["experience"]["minimum_years"] == 5
    assert result["notice_period"]["maximum_days"] == 30
    assert any(s["name"].lower() == "python" for s in result["must_have_skills"])
    assert result["extraction_warnings"][0]["field"] == "provider"


@pytest.mark.asyncio
async def test_mock_provider_extract_resume_structural_validity():
    """Verify MockLLMProvider.extract_resume returns valid schema-compliant dictionary."""
    provider = MockLLMProvider()
    resume_prompt = """
    Aarav Sharma
    aarav.sharma@example.com | +91 98765 43210
    Bangalore, India | 30 days notice | 6 years experience
    Skills: Java, Spring Boot, Python, Docker, PostgreSQL
    Experience: Senior Software Engineer at TechCorp (2020 - Present)
    """
    result = await provider.extract_resume(resume_prompt, output_schema={}, max_tokens=1000)

    assert isinstance(result, dict)
    assert result["full_name"] == "Aarav Sharma"
    assert result["email"] == "aarav.sharma@example.com"
    assert result["notice_period_days"] == 30
    assert result["total_experience_years"] == 6.0
    assert any(s["name"] == "java" for s in result["skills"])
    assert len(result["employment_history"]) >= 1
    assert "MockLLMProvider" in result["warnings"][0]


@pytest.mark.asyncio
async def test_mock_provider_extract_evidence_structural_validity():
    """Verify MockLLMProvider.extract_evidence returns valid schema-compliant dictionary."""
    provider = MockLLMProvider()
    prompt = """
    Evaluate candidate against criteria:
    Criterion ID: c-1111-2222-3333
    Name: Python Programming
    Candidate Resume Text:
    Experienced in Python backend development with FastAPI and Django for 4 years.
    """
    result = await provider.extract_evidence(prompt, output_schema={}, max_tokens=1000)

    assert isinstance(result, dict)
    assert len(result["criteria_evidence"]) >= 1
    matched_item = result["criteria_evidence"][0]
    assert matched_item["criterion_id"] == "c-1111-2222-3333"
    assert matched_item["match_status"] == "MATCHED"
    assert matched_item["confidence"] > 0.8
    assert "python" in matched_item["evidence_text"].lower()


def test_reset_provider():
    """Verify reset_provider clears the global singleton."""
    reset_provider()
    p1 = get_provider()
    assert p1 is not None
    reset_provider()
    p2 = get_provider()
    assert p2 is not None
