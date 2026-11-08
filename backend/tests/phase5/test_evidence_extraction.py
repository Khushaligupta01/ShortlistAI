from __future__ import annotations

import uuid
from typing import Any, Dict
import pytest

from app.ai.evidence_extraction_service import (
    EvidenceExtractionService,
    ProtectedAttributeViolationError,
)
from app.ai.provider import LLMExtractionError, LLMProviderUnavailableError
from app.models.candidate import Candidate, CandidateEmployment, CandidateSkill
from app.models.scorecard import Scorecard, ScorecardCriterion
from app.services.skill_normalization_service import skill_normalizer


class MockLLMProvider:
    """Mock LLM provider returning controlled evidence responses for testing."""
    def __init__(self, response_dict: Dict[str, Any] | None = None, raise_exc: Exception | None = None):
        self.response_dict = response_dict or {}
        self.raise_exc = raise_exc

    async def extract_jd(self, prompt: str, output_schema: dict, max_tokens: int) -> dict:
        return {}

    async def extract_resume(self, prompt: str, output_schema: dict, max_tokens: int) -> dict:
        return {}

    async def extract_evidence(self, prompt: str, output_schema: dict, max_tokens: int) -> dict:
        if self.raise_exc:
            raise self.raise_exc
        return self.response_dict


def make_test_candidate_and_criterion():
    cand = Candidate(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        total_experience_years=7.0,
        location="Noida, India",
        notice_period_days=30,
    )
    s1 = CandidateSkill(
        id=uuid.uuid4(),
        candidate_id=cand.id,
        raw_name="Java",
        name="java",
        evidence="Developed enterprise microservices with Java 17.",
    )
    cand.skills = [s1]

    emp1 = CandidateEmployment(
        id=uuid.uuid4(),
        candidate_id=cand.id,
        company="Tech Corp",
        job_title="Senior Java Developer",
        description="Built resilient message consumers with Apache Kafka.",
        technologies=["Java", "Apache Kafka", "Docker"],
    )
    cand.employments = [emp1]

    crit_java = ScorecardCriterion(
        id=uuid.uuid4(),
        scorecard_id=uuid.uuid4(),
        criterion_type="must_have_skill",
        criterion_name="Java",
        label="Java",
        weight=20,
    )
    crit_spring_boot = ScorecardCriterion(
        id=uuid.uuid4(),
        scorecard_id=uuid.uuid4(),
        criterion_type="must_have_skill",
        criterion_name="Spring Boot",
        label="Spring Boot",
        weight=20,
    )

    resume_text = (
        "ALEX MERCER\n"
        "Senior Java Developer with 7 years of experience in Noida, India.\n"
        "Expert in Java 17, Apache Kafka, and Docker.\n"
        "Notice period: 30 days."
    )
    return cand, [crit_java, crit_spring_boot], resume_text


@pytest.mark.asyncio
async def test_01_evidence_extracted_from_actual_text():
    cand, criteria, resume_text = make_test_candidate_and_criterion()
    service = EvidenceExtractionService(provider=None)  # Use deterministic extractor
    items = await service.extract_evidence(cand, criteria, resume_text)

    java_item = next(it for it in items if it.criterion_name == "Java")
    assert java_item.match_status == "MATCHED"
    assert java_item.confidence >= 0.85
    assert "Java" in java_item.evidence_text


@pytest.mark.asyncio
async def test_02_missing_evidence_is_unknown_or_not_matched():
    cand, _, resume_text = make_test_candidate_and_criterion()
    crit_unknown_tech = ScorecardCriterion(
        id=uuid.uuid4(),
        scorecard_id=uuid.uuid4(),
        criterion_type="must_have_skill",
        criterion_name="Golang",
        label="Golang",
        weight=20,
    )
    service = EvidenceExtractionService(provider=None)
    items = await service.extract_evidence(cand, [crit_unknown_tech], resume_text)

    item = items[0]
    assert item.match_status == "NOT_MATCHED"
    assert item.evidence_text is None


@pytest.mark.asyncio
async def test_03_conflicting_evidence_handling():
    cand, _, resume_text = make_test_candidate_and_criterion()
    crit = ScorecardCriterion(
        id=uuid.uuid4(),
        scorecard_id=uuid.uuid4(),
        criterion_type="experience",
        criterion_name="Experience",
        label="Experience",
        weight=30,
    )
    # Mock LLM returning conflicting status
    mock_resp = {
        "criteria_evidence": [
            {
                "criterion_id": str(crit.id),
                "criterion_name": "Experience",
                "match_status": "CONFLICTING",
                "confidence": 0.40,
                "evidence_text": "Dates in resume indicate overlapping full-time employment at two companies.",
                "explanation": "Conflicting employment dates detected.",
            }
        ]
    }
    service = EvidenceExtractionService(provider=MockLLMProvider(mock_resp))
    items = await service.extract_evidence(cand, [crit], resume_text)

    item = items[0]
    assert item.match_status == "CONFLICTING"
    assert item.confidence == 0.40


@pytest.mark.asyncio
async def test_04_malformed_ai_response_handling():
    cand, criteria, resume_text = make_test_candidate_and_criterion()
    # Mock LLM returning completely invalid dictionary structure
    mock_resp = {"bad_key": 1234}
    service = EvidenceExtractionService(provider=MockLLMProvider(mock_resp))
    # Should safely fall back to deterministic extraction without throwing an unhandled exception
    items = await service.extract_evidence(cand, criteria, resume_text)
    assert len(items) == 2
    assert items[0].match_status in ("MATCHED", "PARTIAL", "NOT_MATCHED", "UNKNOWN")


@pytest.mark.asyncio
async def test_05_anti_fabrication_unsupported_evidence_downgraded():
    cand, criteria, resume_text = make_test_candidate_and_criterion()
    crit = criteria[0]
    # Mock LLM returning a completely fabricated quotation that does not exist in the resume
    mock_resp = {
        "criteria_evidence": [
            {
                "criterion_id": str(crit.id),
                "criterion_name": crit.criterion_name,
                "match_status": "MATCHED",
                "confidence": 0.95,
                "evidence_text": "I am a world champion Java kernel developer who rewrote the HotSpot JVM from scratch in 2024.",
                "explanation": "World champion developer.",
            }
        ]
    }
    service = EvidenceExtractionService(provider=MockLLMProvider(mock_resp))
    items = await service.extract_evidence(cand, [crit], resume_text)

    item = items[0]
    # Verify that unverified excerpt triggers a confidence penalty and unverified flag
    assert item.confidence < 0.50
    assert "[Unverified Excerpt]" in (item.explanation or "")


@pytest.mark.asyncio
async def test_06_source_location_preservation():
    cand, criteria, resume_text = make_test_candidate_and_criterion()
    service = EvidenceExtractionService(provider=None)
    items = await service.extract_evidence(cand, criteria, resume_text)
    java_item = next(it for it in items if it.criterion_name == "Java")
    assert java_item.source_reference is not None


def test_07_controlled_skill_normalization():
    assert skill_normalizer.normalize("Java") == "java"
    assert skill_normalizer.normalize("Core Java") == "java"
    assert skill_normalizer.normalize("React.js") == "react"
    assert skill_normalizer.normalize("ReactJS") == "react"
    assert skill_normalizer.normalize("PostgreSQL") == "postgresql"
    assert skill_normalizer.normalize("K8s") == "kubernetes"


def test_08_spring_vs_spring_boot_distinction():
    # Spring Boot and Spring Framework MUST remain distinct canonical skills
    assert skill_normalizer.normalize("Spring Boot") == "spring_boot"
    assert skill_normalizer.normalize("Spring") == "spring_framework"
    assert skill_normalizer.normalize("Spring Framework") == "spring_framework"

    assert not skill_normalizer.is_match("Spring", "Spring Boot")
    assert not skill_normalizer.is_match("Java", "JavaScript")
    assert not skill_normalizer.is_match("C", "C++")
    assert not skill_normalizer.is_match("C++", "C#")


@pytest.mark.asyncio
async def test_09_ai_provider_timeout_fallback():
    cand, criteria, resume_text = make_test_candidate_and_criterion()
    mock_provider = MockLLMProvider(raise_exc=LLMExtractionError("Timeout waiting for LLM", retryable=True))
    service = EvidenceExtractionService(provider=mock_provider)
    # Falls back gracefully to deterministic extractor
    items = await service.extract_evidence(cand, criteria, resume_text)
    assert len(items) == len(criteria)
    assert any(it.match_status == "MATCHED" for it in items)


@pytest.mark.asyncio
async def test_10_ai_provider_unavailable_fallback():
    cand, criteria, resume_text = make_test_candidate_and_criterion()
    mock_provider = MockLLMProvider(raise_exc=LLMProviderUnavailableError("OpenAI API key not set"))
    service = EvidenceExtractionService(provider=mock_provider)
    items = await service.extract_evidence(cand, criteria, resume_text)
    assert len(items) == len(criteria)
    assert items[0].match_status == "MATCHED"
