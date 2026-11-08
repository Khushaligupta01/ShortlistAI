from __future__ import annotations

import uuid
from decimal import Decimal
import pytest

from app.ai.schemas import CriterionEvidenceItem
from app.models.candidate import Candidate
from app.models.scorecard import Scorecard, ScorecardCriterion
from app.services.scoring_engine_service import scoring_engine


def make_test_scorecard() -> Scorecard:
    """Creates a standard Senior Java Developer scorecard with 100 total weight."""
    sc = Scorecard(
        id=uuid.uuid4(),
        requisition_id=uuid.uuid4(),
        version_number=1,
        status="approved",
        experience_min=5,
        experience_max=8,
        location="Noida",
        max_notice_days=60,
        total_weight=100,
        scoring_config={
            "experience": 30,
            "must_have_skills": 40,
            "notice_period": 15,
            "location": 10,
            "nice_to_have_skills": 5,
        },
    )

    c_exp = ScorecardCriterion(
        id=uuid.uuid4(),
        scorecard_id=sc.id,
        criterion_type="experience",
        criterion_name="5-8 Years Experience",
        label="Experience",
        weight=30,
        is_mandatory=True,
        config_json={"min_years": 5.0, "max_years": 8.0},
    )
    c_java = ScorecardCriterion(
        id=uuid.uuid4(),
        scorecard_id=sc.id,
        criterion_type="must_have_skill",
        criterion_name="Java",
        label="Core Java",
        weight=20,
        is_mandatory=True,
        config_json={"skill_name": "Java"},
    )
    c_spring = ScorecardCriterion(
        id=uuid.uuid4(),
        scorecard_id=sc.id,
        criterion_type="must_have_skill",
        criterion_name="Spring Boot",
        label="Spring Boot",
        weight=20,
        is_mandatory=True,
        config_json={"skill_name": "Spring Boot"},
    )
    c_notice = ScorecardCriterion(
        id=uuid.uuid4(),
        scorecard_id=sc.id,
        criterion_type="notice_period",
        criterion_name="Max 60 Days Notice",
        label="Notice Period",
        weight=15,
        is_mandatory=True,
        config_json={"max_notice_days": 60},
    )
    c_loc = ScorecardCriterion(
        id=uuid.uuid4(),
        scorecard_id=sc.id,
        criterion_type="location",
        criterion_name="Noida",
        label="Job Location",
        weight=10,
        is_mandatory=True,
        config_json={"location": "Noida"},
    )
    c_nth = ScorecardCriterion(
        id=uuid.uuid4(),
        scorecard_id=sc.id,
        criterion_type="nice_to_have_skill",
        criterion_name="Microservices",
        label="Microservices Architecture",
        weight=5,
        is_mandatory=False,
        config_json={"skill_name": "Microservices"},
    )

    sc.criteria = [c_exp, c_java, c_spring, c_notice, c_loc, c_nth]
    return sc


def test_01_experience_within_range():
    sc = make_test_scorecard()
    c_exp = sc.criteria[0]
    cand = Candidate(id=uuid.uuid4(), organization_id=uuid.uuid4(), total_experience_years=6.5)
    ev = [
        CriterionEvidenceItem(
            criterion_id=str(c_exp.id),
            criterion_name=c_exp.criterion_name,
            match_status="MATCHED",
            confidence=0.95,
            evidence_text="6.5 years experience in Java backend development.",
        )
    ]
    res = scoring_engine.compute_scores(cand, sc, ev)
    exp_res = next(r for r in res.criteria_results if r.criterion_id == str(c_exp.id))
    assert exp_res.awarded_points == 30.0
    assert exp_res.match_status == "MATCHED"


def test_02_experience_below_minimum():
    sc = make_test_scorecard()
    c_exp = sc.criteria[0]
    # 3.0 years vs 5.0 min required: 30 * (3.0 / 5.0) = 18.0
    cand = Candidate(id=uuid.uuid4(), organization_id=uuid.uuid4(), total_experience_years=3.0)
    ev = [
        CriterionEvidenceItem(
            criterion_id=str(c_exp.id),
            criterion_name=c_exp.criterion_name,
            match_status="PARTIAL",
            confidence=0.90,
            evidence_text="3.0 years software engineer.",
        )
    ]
    res = scoring_engine.compute_scores(cand, sc, ev)
    exp_res = next(r for r in res.criteria_results if r.criterion_id == str(c_exp.id))
    assert exp_res.awarded_points == 18.0
    assert exp_res.match_status == "PARTIAL"


def test_03_experience_above_maximum_not_penalized():
    sc = make_test_scorecard()
    c_exp = sc.criteria[0]
    cand = Candidate(id=uuid.uuid4(), organization_id=uuid.uuid4(), total_experience_years=12.0)
    ev = [
        CriterionEvidenceItem(
            criterion_id=str(c_exp.id),
            criterion_name=c_exp.criterion_name,
            match_status="MATCHED",
            confidence=0.95,
        )
    ]
    res = scoring_engine.compute_scores(cand, sc, ev)
    exp_res = next(r for r in res.criteria_results if r.criterion_id == str(c_exp.id))
    # Above max is not penalized automatically; candidate meets the experience requirement
    assert exp_res.awarded_points == 30.0


def test_04_missing_experience_treated_as_unknown():
    sc = make_test_scorecard()
    c_exp = sc.criteria[0]
    cand = Candidate(id=uuid.uuid4(), organization_id=uuid.uuid4(), total_experience_years=None)
    ev = [
        CriterionEvidenceItem(
            criterion_id=str(c_exp.id),
            criterion_name=c_exp.criterion_name,
            match_status="UNKNOWN",
            confidence=0.50,
        )
    ]
    res = scoring_engine.compute_scores(cand, sc, ev)
    exp_res = next(r for r in res.criteria_results if r.criterion_id == str(c_exp.id))
    assert exp_res.awarded_points == 0.0
    assert exp_res.match_status == "UNKNOWN"


def test_05_all_must_have_skills_matched():
    sc = make_test_scorecard()
    c_java = sc.criteria[1]
    c_spring = sc.criteria[2]
    cand = Candidate(id=uuid.uuid4(), organization_id=uuid.uuid4())
    ev = [
        CriterionEvidenceItem(criterion_id=str(c_java.id), criterion_name=c_java.criterion_name, match_status="MATCHED", confidence=0.95),
        CriterionEvidenceItem(criterion_id=str(c_spring.id), criterion_name=c_spring.criterion_name, match_status="MATCHED", confidence=0.95),
    ]
    res = scoring_engine.compute_scores(cand, sc, ev)
    assert res.category_scores["must_have_skills"]["awarded"] == 40.0


def test_06_partial_must_have_skill_credit():
    sc = make_test_scorecard()
    c_java = sc.criteria[1]
    c_spring = sc.criteria[2]
    cand = Candidate(id=uuid.uuid4(), organization_id=uuid.uuid4())
    # Java matched (20), Spring Boot partial (50% of 20 = 10) -> total 30
    ev = [
        CriterionEvidenceItem(criterion_id=str(c_java.id), criterion_name=c_java.criterion_name, match_status="MATCHED", confidence=0.95),
        CriterionEvidenceItem(criterion_id=str(c_spring.id), criterion_name=c_spring.criterion_name, match_status="PARTIAL", confidence=0.75),
    ]
    res = scoring_engine.compute_scores(cand, sc, ev)
    assert res.category_scores["must_have_skills"]["awarded"] == 30.0


def test_07_missing_skill_evidence_zero_points():
    sc = make_test_scorecard()
    c_java = sc.criteria[1]
    c_spring = sc.criteria[2]
    cand = Candidate(id=uuid.uuid4(), organization_id=uuid.uuid4())
    ev = [
        CriterionEvidenceItem(criterion_id=str(c_java.id), criterion_name=c_java.criterion_name, match_status="NOT_MATCHED", confidence=0.90),
        CriterionEvidenceItem(criterion_id=str(c_spring.id), criterion_name=c_spring.criterion_name, match_status="NOT_MATCHED", confidence=0.90),
    ]
    res = scoring_engine.compute_scores(cand, sc, ev)
    assert res.category_scores["must_have_skills"]["awarded"] == 0.0


def test_08_unknown_notice_period():
    sc = make_test_scorecard()
    c_notice = sc.criteria[3]
    cand = Candidate(id=uuid.uuid4(), organization_id=uuid.uuid4(), notice_period_days=None)
    ev = [
        CriterionEvidenceItem(criterion_id=str(c_notice.id), criterion_name=c_notice.criterion_name, match_status="UNKNOWN", confidence=0.50),
    ]
    res = scoring_engine.compute_scores(cand, sc, ev)
    np_res = next(r for r in res.criteria_results if r.criterion_id == str(c_notice.id))
    assert np_res.awarded_points == 0.0
    assert np_res.match_status == "UNKNOWN"


def test_09_notice_period_within_max():
    sc = make_test_scorecard()
    c_notice = sc.criteria[3]
    cand = Candidate(id=uuid.uuid4(), organization_id=uuid.uuid4(), notice_period_days=30)
    ev = [
        CriterionEvidenceItem(criterion_id=str(c_notice.id), criterion_name=c_notice.criterion_name, match_status="MATCHED", confidence=0.95),
    ]
    res = scoring_engine.compute_scores(cand, sc, ev)
    np_res = next(r for r in res.criteria_results if r.criterion_id == str(c_notice.id))
    assert np_res.awarded_points == 15.0


def test_10_notice_period_above_max():
    sc = make_test_scorecard()
    c_notice = sc.criteria[3]
    # 90 days vs 60 days max (within 1.5x): 15 * (60 / 90) = 10.0
    cand = Candidate(id=uuid.uuid4(), organization_id=uuid.uuid4(), notice_period_days=90)
    ev = [
        CriterionEvidenceItem(criterion_id=str(c_notice.id), criterion_name=c_notice.criterion_name, match_status="PARTIAL", confidence=0.90),
    ]
    res = scoring_engine.compute_scores(cand, sc, ev)
    np_res = next(r for r in res.criteria_results if r.criterion_id == str(c_notice.id))
    assert np_res.awarded_points == 10.0


def test_11_matching_location():
    sc = make_test_scorecard()
    c_loc = sc.criteria[4]
    cand = Candidate(id=uuid.uuid4(), organization_id=uuid.uuid4(), location="Noida, India")
    ev = [
        CriterionEvidenceItem(criterion_id=str(c_loc.id), criterion_name=c_loc.criterion_name, match_status="MATCHED", confidence=0.95),
    ]
    res = scoring_engine.compute_scores(cand, sc, ev)
    loc_res = next(r for r in res.criteria_results if r.criterion_id == str(c_loc.id))
    assert loc_res.awarded_points == 10.0


def test_12_missing_location():
    sc = make_test_scorecard()
    c_loc = sc.criteria[4]
    cand = Candidate(id=uuid.uuid4(), organization_id=uuid.uuid4(), location=None)
    ev = [
        CriterionEvidenceItem(criterion_id=str(c_loc.id), criterion_name=c_loc.criterion_name, match_status="UNKNOWN", confidence=0.50),
    ]
    res = scoring_engine.compute_scores(cand, sc, ev)
    loc_res = next(r for r in res.criteria_results if r.criterion_id == str(c_loc.id))
    assert loc_res.awarded_points == 0.0
    assert loc_res.match_status == "UNKNOWN"


def test_13_nice_to_have_matches():
    sc = make_test_scorecard()
    c_nth = sc.criteria[5]
    cand = Candidate(id=uuid.uuid4(), organization_id=uuid.uuid4())
    ev = [
        CriterionEvidenceItem(criterion_id=str(c_nth.id), criterion_name=c_nth.criterion_name, match_status="MATCHED", confidence=0.95),
    ]
    res = scoring_engine.compute_scores(cand, sc, ev)
    nth_res = next(r for r in res.criteria_results if r.criterion_id == str(c_nth.id))
    assert nth_res.awarded_points == 5.0


def test_14_deterministic_repeated_calculation():
    sc = make_test_scorecard()
    cand = Candidate(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        total_experience_years=7.0,
        notice_period_days=45,
        location="Noida",
    )
    ev = [
        CriterionEvidenceItem(criterion_id=str(sc.criteria[0].id), criterion_name="Exp", match_status="MATCHED", confidence=0.95),
        CriterionEvidenceItem(criterion_id=str(sc.criteria[1].id), criterion_name="Java", match_status="MATCHED", confidence=0.95),
        CriterionEvidenceItem(criterion_id=str(sc.criteria[2].id), criterion_name="Spring Boot", match_status="PARTIAL", confidence=0.80),
        CriterionEvidenceItem(criterion_id=str(sc.criteria[3].id), criterion_name="Notice", match_status="MATCHED", confidence=0.95),
        CriterionEvidenceItem(criterion_id=str(sc.criteria[4].id), criterion_name="Location", match_status="MATCHED", confidence=0.95),
        CriterionEvidenceItem(criterion_id=str(sc.criteria[5].id), criterion_name="Microservices", match_status="MATCHED", confidence=0.90),
    ]

    first_res = scoring_engine.compute_scores(cand, sc, ev)

    for _ in range(10):
        subsequent_res = scoring_engine.compute_scores(cand, sc, ev)
        assert subsequent_res.raw_score == first_res.raw_score
        assert subsequent_res.normalized_score == first_res.normalized_score
        assert subsequent_res.evidence_coverage == first_res.evidence_coverage
        assert subsequent_res.confidence_level == first_res.confidence_level


def test_15_score_boundaries_and_clamping():
    sc = make_test_scorecard()
    cand = Candidate(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        total_experience_years=8.0,
        notice_period_days=15,
        location="Noida",
    )
    ev = [
        CriterionEvidenceItem(criterion_id=str(c.id), criterion_name=c.criterion_name, match_status="MATCHED", confidence=0.99)
        for c in sc.criteria
    ]
    res = scoring_engine.compute_scores(cand, sc, ev)
    assert 0.0 <= res.raw_score <= 100.0
    assert 0.0 <= res.normalized_score <= 100.0
    assert res.raw_score == 100.0
    assert res.normalized_score == 100.0


def test_16_unknown_data_provisional_normalization():
    sc = make_test_scorecard()
    # Candidate meets experience (30) and Java (20), but notice and location are unknown
    cand = Candidate(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        total_experience_years=6.0,
        notice_period_days=None,
        location=None,
    )
    ev = [
        CriterionEvidenceItem(criterion_id=str(sc.criteria[0].id), criterion_name="Exp", match_status="MATCHED", confidence=0.95),
        CriterionEvidenceItem(criterion_id=str(sc.criteria[1].id), criterion_name="Java", match_status="MATCHED", confidence=0.95),
        CriterionEvidenceItem(criterion_id=str(sc.criteria[2].id), criterion_name="Spring Boot", match_status="NOT_MATCHED", confidence=0.90),
        CriterionEvidenceItem(criterion_id=str(sc.criteria[3].id), criterion_name="Notice", match_status="UNKNOWN", confidence=0.50),
        CriterionEvidenceItem(criterion_id=str(sc.criteria[4].id), criterion_name="Location", match_status="UNKNOWN", confidence=0.50),
        CriterionEvidenceItem(criterion_id=str(sc.criteria[5].id), criterion_name="Microservices", match_status="NOT_MATCHED", confidence=0.90),
    ]
    res = scoring_engine.compute_scores(cand, sc, ev)
    # Raw points earned = 30 (exp) + 20 (java) = 50.0
    assert res.raw_score == 50.0

    # Known criteria: exp (30), java (20), spring boot (20), microservices (5) = sum 75.0
    # Provisional normalized score: 50 / 75 * 100 = 66.67
    assert res.normalized_score == 66.67
    # Evidence coverage: 4 known out of 6 total = 66.7%
    assert res.evidence_coverage == 66.7
    assert res.confidence_level == "NEEDS_REVIEW"


def test_17_evidence_coverage_calculation():
    sc = make_test_scorecard()
    cand = Candidate(id=uuid.uuid4(), organization_id=uuid.uuid4())
    # All 6 criteria UNKNOWN
    ev = [
        CriterionEvidenceItem(criterion_id=str(c.id), criterion_name=c.criterion_name, match_status="UNKNOWN", confidence=0.50)
        for c in sc.criteria
    ]
    res = scoring_engine.compute_scores(cand, sc, ev)
    assert res.evidence_coverage == 0.0
    assert res.raw_score == 0.0
    assert res.confidence_level == "LOW"
