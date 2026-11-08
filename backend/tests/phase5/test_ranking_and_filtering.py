from __future__ import annotations

import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.evaluation import Evaluation
from app.models.organization import Organization
from app.models.requisition import Requisition
from app.models.scorecard import Scorecard
from app.models.user import User
from app.services.ranking_service import ranking_service


@pytest.fixture
async def setup_ranking_data(db_session: AsyncSession):
    # Create Organization 1 and Requisition
    org1 = Organization(id=uuid.uuid4(), name="Tech Recruiting Corp", org_type="staffing_firm")
    org2 = Organization(id=uuid.uuid4(), name="Other Recruiting Corp", org_type="staffing_firm")
    db_session.add_all([org1, org2])
    await db_session.flush()

    user = User(
        id=uuid.uuid4(),
        email=f"recruiter_{uuid.uuid4().hex[:6]}@techrecruiting.com",
        password_hash="fakehash",
        display_name="Recruiter",
    )
    db_session.add(user)
    await db_session.flush()

    req = Requisition(
        id=uuid.uuid4(),
        organization_id=org1.id,
        created_by=user.id,
        title="Senior Java Developer",
        job_description="Java, Spring Boot, 5+ years experience.",
        status="active",
    )
    db_session.add(req)
    await db_session.flush()

    sc = Scorecard(
        id=uuid.uuid4(),
        requisition_id=req.id,
        version_number=1,
        status="approved",
        total_weight=100,
    )
    db_session.add(sc)
    await db_session.flush()

    # Create 5 candidates with various scores in Org 1
    # Candidate A: High score 95.0, high confidence, full coverage
    cand_a = Candidate(id=uuid.uuid4(), organization_id=org1.id, full_name="Alice Smith", email="alice@example.com", total_experience_years=8.0)
    # Candidate B: High score 95.0, tied with A (tie breaker test)
    cand_b = Candidate(id=uuid.uuid4(), organization_id=org1.id, full_name="Bob Jones", email="bob@example.com", total_experience_years=6.0)
    # Candidate C: Medium score 65.0, missing evidence, needs review
    cand_c = Candidate(id=uuid.uuid4(), organization_id=org1.id, full_name="Charlie Brown", email="charlie@example.com", total_experience_years=4.0)
    # Candidate D: Low score 20.0, low confidence (must NOT be deleted or hidden!)
    cand_d = Candidate(id=uuid.uuid4(), organization_id=org1.id, full_name="David Miller", email="david@example.com", total_experience_years=1.0)

    # Candidate E: Belongs to Org 2 (Org isolation test)
    cand_e = Candidate(id=uuid.uuid4(), organization_id=org2.id, full_name="Eve Hacker", email="eve@other.com", total_experience_years=10.0)

    db_session.add_all([cand_a, cand_b, cand_c, cand_d, cand_e])
    await db_session.flush()

    eval_a = Evaluation(
        id=uuid.uuid4(),
        candidate_id=cand_a.id,
        requisition_id=req.id,
        scorecard_id=sc.id,
        organization_id=org1.id,
        total_score=95.0,
        raw_score=95.0,
        normalized_score=95.0,
        evidence_coverage=100.0,
        confidence_level="HIGH",
        is_current=True,
    )
    eval_b = Evaluation(
        id=uuid.uuid4(),
        candidate_id=cand_b.id,
        requisition_id=req.id,
        scorecard_id=sc.id,
        organization_id=org1.id,
        total_score=95.0,
        raw_score=95.0,
        normalized_score=95.0,
        evidence_coverage=90.0,
        confidence_level="HIGH",
        is_current=True,
    )
    eval_c = Evaluation(
        id=uuid.uuid4(),
        candidate_id=cand_c.id,
        requisition_id=req.id,
        scorecard_id=sc.id,
        organization_id=org1.id,
        total_score=65.0,
        raw_score=45.0,
        normalized_score=65.0,
        evidence_coverage=60.0,
        confidence_level="NEEDS_REVIEW",
        is_current=True,
    )
    eval_d = Evaluation(
        id=uuid.uuid4(),
        candidate_id=cand_d.id,
        requisition_id=req.id,
        scorecard_id=sc.id,
        organization_id=org1.id,
        total_score=20.0,
        raw_score=20.0,
        normalized_score=20.0,
        evidence_coverage=40.0,
        confidence_level="LOW",
        is_current=True,
    )
    eval_e = Evaluation(
        id=uuid.uuid4(),
        candidate_id=cand_e.id,
        requisition_id=req.id,
        scorecard_id=sc.id,
        organization_id=org2.id,
        total_score=99.0,
        raw_score=99.0,
        normalized_score=99.0,
        evidence_coverage=100.0,
        confidence_level="HIGH",
        is_current=True,
    )
    db_session.add_all([eval_a, eval_b, eval_c, eval_d, eval_e])
    await db_session.commit()

    return {
        "org1_id": org1.id,
        "org2_id": org2.id,
        "req_id": req.id,
        "cand_a_id": cand_a.id,
        "cand_b_id": cand_b.id,
        "cand_c_id": cand_c.id,
        "cand_d_id": cand_d.id,
    }


@pytest.mark.asyncio
async def test_01_descending_score_ranking(db_session: AsyncSession, setup_ranking_data):
    data = setup_ranking_data
    evals, total = await ranking_service.list_ranked_evaluations(
        db=db_session,
        requisition_id=data["req_id"],
        organization_id=data["org1_id"],
        sort_by="score_desc",
    )
    assert total == 4
    scores = [float(e.normalized_score) for e in evals]
    # Scores must be sorted descending: [95.0, 95.0, 65.0, 20.0]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_02_ascending_score_ranking(db_session: AsyncSession, setup_ranking_data):
    data = setup_ranking_data
    evals, total = await ranking_service.list_ranked_evaluations(
        db=db_session,
        requisition_id=data["req_id"],
        organization_id=data["org1_id"],
        sort_by="score_asc",
    )
    assert total == 4
    scores = [float(e.normalized_score) for e in evals]
    assert scores == sorted(scores)
    assert scores[0] == 20.0


@pytest.mark.asyncio
async def test_03_tied_score_deterministic_tiebreaking(db_session: AsyncSession, setup_ranking_data):
    data = setup_ranking_data
    # Both A and B have 95.0 score.
    # Candidate A has 100.0% coverage, Candidate B has 90.0% coverage.
    # A should rank before B.
    evals, _ = await ranking_service.list_ranked_evaluations(
        db=db_session,
        requisition_id=data["req_id"],
        organization_id=data["org1_id"],
        sort_by="score_desc",
    )
    top_two = evals[:2]
    assert top_two[0].candidate_id == data["cand_a_id"]
    assert top_two[1].candidate_id == data["cand_b_id"]


@pytest.mark.asyncio
async def test_04_confidence_level_filtering(db_session: AsyncSession, setup_ranking_data):
    data = setup_ranking_data
    # Filter for NEEDS_REVIEW
    evals, total = await ranking_service.list_ranked_evaluations(
        db=db_session,
        requisition_id=data["req_id"],
        organization_id=data["org1_id"],
        confidence_level="NEEDS_REVIEW",
    )
    assert total == 1
    assert evals[0].candidate_id == data["cand_c_id"]


@pytest.mark.asyncio
async def test_05_missing_evidence_filtering(db_session: AsyncSession, setup_ranking_data):
    data = setup_ranking_data
    # Filter for candidates with missing evidence (< 80% coverage: C and D)
    evals, total = await ranking_service.list_ranked_evaluations(
        db=db_session,
        requisition_id=data["req_id"],
        organization_id=data["org1_id"],
        missing_evidence_only=True,
    )
    assert total == 2
    cand_ids = {e.candidate_id for e in evals}
    assert cand_ids == {data["cand_c_id"], data["cand_d_id"]}


@pytest.mark.asyncio
async def test_06_low_scoring_candidate_remains_visible(db_session: AsyncSession, setup_ranking_data):
    data = setup_ranking_data
    # Candidate D scored 20.0 / 100. They MUST remain visible in the list!
    evals, total = await ranking_service.list_ranked_evaluations(
        db=db_session,
        requisition_id=data["req_id"],
        organization_id=data["org1_id"],
    )
    assert any(e.candidate_id == data["cand_d_id"] for e in evals)
    # Check that score_min filter behaves as expected
    filtered, _ = await ranking_service.list_ranked_evaluations(
        db=db_session,
        requisition_id=data["req_id"],
        organization_id=data["org1_id"],
        score_min=50.0,
    )
    assert all(float(e.normalized_score) >= 50.0 for e in filtered)


@pytest.mark.asyncio
async def test_07_pagination(db_session: AsyncSession, setup_ranking_data):
    data = setup_ranking_data
    page1, total = await ranking_service.list_ranked_evaluations(
        db=db_session,
        requisition_id=data["req_id"],
        organization_id=data["org1_id"],
        page=1,
        page_size=2,
    )
    page2, _ = await ranking_service.list_ranked_evaluations(
        db=db_session,
        requisition_id=data["req_id"],
        organization_id=data["org1_id"],
        page=2,
        page_size=2,
    )
    assert total == 4
    assert len(page1) == 2
    assert len(page2) == 2
    assert page1[0].id != page2[0].id


@pytest.mark.asyncio
async def test_08_organization_isolation(db_session: AsyncSession, setup_ranking_data):
    data = setup_ranking_data
    # Org 1 evaluations must NOT include Candidate E from Org 2 (who scored 99.0)
    evals, total = await ranking_service.list_ranked_evaluations(
        db=db_session,
        requisition_id=data["req_id"],
        organization_id=data["org1_id"],
    )
    assert total == 4
    for ev in evals:
        assert ev.candidate.organization_id == data["org1_id"]

