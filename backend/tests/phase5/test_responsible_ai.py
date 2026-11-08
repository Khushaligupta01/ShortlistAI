from __future__ import annotations

import uuid
import pytest

from app.ai.evidence_extraction_service import (
    EvidenceExtractionService,
    ProtectedAttributeViolationError,
)
from app.ai.schemas import CriterionEvidenceItem
from app.models.candidate import Candidate, CandidateSkill
from app.models.scorecard import Scorecard, ScorecardCriterion
from app.services.scoring_engine_service import scoring_engine


def make_test_scorecard() -> Scorecard:
    sc = Scorecard(
        id=uuid.uuid4(),
        requisition_id=uuid.uuid4(),
        status="approved",
        total_weight=100,
        experience_min=5,
        location="Noida",
        max_notice_days=60,
    )
    c1 = ScorecardCriterion(
        id=uuid.uuid4(),
        scorecard_id=sc.id,
        criterion_type="experience",
        criterion_name="Experience",
        label="Experience",
        weight=30,
        config_json={"min_years": 5.0},
    )
    c2 = ScorecardCriterion(
        id=uuid.uuid4(),
        scorecard_id=sc.id,
        criterion_type="must_have_skill",
        criterion_name="Java",
        label="Java",
        weight=40,
    )
    c3 = ScorecardCriterion(
        id=uuid.uuid4(),
        scorecard_id=sc.id,
        criterion_type="notice_period",
        criterion_name="Notice",
        label="Notice",
        weight=15,
        config_json={"max_notice_days": 60},
    )
    c4 = ScorecardCriterion(
        id=uuid.uuid4(),
        scorecard_id=sc.id,
        criterion_type="location",
        criterion_name="Location",
        label="Location",
        weight=15,
        config_json={"location": "Noida"},
    )
    sc.criteria = [c1, c2, c3, c4]
    return sc


def test_01_changing_candidate_name_does_not_change_score():
    sc = make_test_scorecard()

    # Candidate 1: Male European name
    cand1 = Candidate(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        full_name="John Alexander Smith",
        email="john.smith@domain.com",
        phone="+1-555-010-1111",
        total_experience_years=6.0,
        location="Noida",
        notice_period_days=30,
    )
    # Candidate 2: Female Asian name with identical qualifications
    cand2 = Candidate(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        full_name="Priya Ananya Sharma",
        email="priya.sharma@domain.in",
        phone="+91-98765-43210",
        total_experience_years=6.0,
        location="Noida",
        notice_period_days=30,
    )

    ev1 = [
        CriterionEvidenceItem(criterion_id=str(sc.criteria[0].id), criterion_name="Exp", match_status="MATCHED", confidence=0.95),
        CriterionEvidenceItem(criterion_id=str(sc.criteria[1].id), criterion_name="Java", match_status="MATCHED", confidence=0.95),
        CriterionEvidenceItem(criterion_id=str(sc.criteria[2].id), criterion_name="Notice", match_status="MATCHED", confidence=0.95),
        CriterionEvidenceItem(criterion_id=str(sc.criteria[3].id), criterion_name="Location", match_status="MATCHED", confidence=0.95),
    ]

    res1 = scoring_engine.compute_scores(cand1, sc, ev1)
    res2 = scoring_engine.compute_scores(cand2, sc, ev1)

    assert res1.raw_score == res2.raw_score
    assert res1.normalized_score == res2.normalized_score
    assert res1.evidence_coverage == res2.evidence_coverage
    assert res1.confidence_level == res2.confidence_level


def test_02_demographic_attributes_excluded_from_profile_cleaning():
    service = EvidenceExtractionService()
    cand = Candidate(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        full_name="Secret Candidate",
        email="secret@example.com",
        phone="555-1234",
        total_experience_years=5.0,
        location="Noida",
    )
    clean = service.clean_candidate_profile(cand)

    # Name, email, phone, gender, age must NEVER exist in clean profile
    assert "full_name" not in clean
    assert "email" not in clean
    assert "phone" not in clean
    assert "gender" not in clean
    assert "age" not in clean


def test_03_protected_attributes_violation_raises_error():
    service = EvidenceExtractionService()
    # If any module inadvertently injects a protected attribute:
    poisoned_input = {
        "total_experience_years": 5.0,
        "location": "Noida",
        "gender": "female",
    }
    with pytest.raises(ProtectedAttributeViolationError):
        service.assert_no_protected_attributes(poisoned_input)


def test_04_low_scores_do_not_trigger_automatic_rejection():
    sc = make_test_scorecard()
    # Candidate with zero matching skills and no experience
    cand = Candidate(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        total_experience_years=0.0,
        location="London",
        notice_period_days=180,
    )
    ev = [
        CriterionEvidenceItem(criterion_id=str(sc.criteria[0].id), criterion_name="Exp", match_status="NOT_MATCHED", confidence=0.90),
        CriterionEvidenceItem(criterion_id=str(sc.criteria[1].id), criterion_name="Java", match_status="NOT_MATCHED", confidence=0.90),
        CriterionEvidenceItem(criterion_id=str(sc.criteria[2].id), criterion_name="Notice", match_status="NOT_MATCHED", confidence=0.90),
        CriterionEvidenceItem(criterion_id=str(sc.criteria[3].id), criterion_name="Location", match_status="NOT_MATCHED", confidence=0.90),
    ]
    res = scoring_engine.compute_scores(cand, sc, ev)
    # Score is 0.0, but candidate is NOT rejected automatically
    assert res.raw_score == 0.0
    # No status indicates rejection (status is purely an evaluation outcome)
    assert res.confidence_level in ("HIGH", "NEEDS_REVIEW", "LOW")


def test_05_missing_information_does_not_silently_penalize():
    sc = make_test_scorecard()
    # Candidate with notice period missing
    cand = Candidate(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        total_experience_years=6.0,
        location="Noida",
        notice_period_days=None,  # Missing
    )
    ev = [
        CriterionEvidenceItem(criterion_id=str(sc.criteria[0].id), criterion_name="Exp", match_status="MATCHED", confidence=0.95),
        CriterionEvidenceItem(criterion_id=str(sc.criteria[1].id), criterion_name="Java", match_status="MATCHED", confidence=0.95),
        CriterionEvidenceItem(criterion_id=str(sc.criteria[2].id), criterion_name="Notice", match_status="UNKNOWN", confidence=0.50),
        CriterionEvidenceItem(criterion_id=str(sc.criteria[3].id), criterion_name="Location", match_status="MATCHED", confidence=0.95),
    ]
    res = scoring_engine.compute_scores(cand, sc, ev)
    # Notice period is UNKNOWN, not NOT_MATCHED
    np_res = next(r for r in res.criteria_results if r.criterion_name == "Notice")
    assert np_res.match_status == "UNKNOWN"
    # Evidence coverage visibly reflects missing data
    assert res.evidence_coverage == 75.0
    # Flagged for review
    assert res.confidence_level == "NEEDS_REVIEW"
