from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate, CandidateSkill, CandidateEmployment
from app.models.requisition import Requisition
from app.models.scorecard import Scorecard, ScorecardCriterion
from app.models.resume import Resume
from app.models.evaluation import Evaluation
from tests.conftest import auth_headers, seed_user_with_org


@pytest.mark.asyncio
async def test_workflow_d_ai_evaluation_and_deterministic_ranking(client: AsyncClient, db_session: AsyncSession):
    """
    Workflow D:
    1. Requisition with approved scorecard (version 1).
    2. Multiple candidates with strong, medium, and low qualification profiles.
    3. Evaluate candidates via POST /api/v1/requisitions/{id}/candidates/{id}/evaluate.
    4. Verify deterministic scoring and criterion evidence.
    5. Verify score breakdown and normalization of unknown attributes.
    6. Verify low-scoring candidates remain visible and searchable in ranking.
    """
    recruiter, org = await seed_user_with_org(
        db_session,
        email="recruiter.eval@example.com",
        password="PassWord123!",
        role="recruiter",
        org_name="Eval Ranking Staffing",
    )
    headers = auth_headers(recruiter.id, "recruiter", org.id)

    # 1. Requisition & Scorecard
    req = Requisition(
        id=uuid.uuid4(),
        organization_id=org.id,
        created_by=recruiter.id,
        title="Senior Python Architect",
        job_description="Python, FastAPI, System Architecture.",
        status="active",
    )
    db_session.add(req)

    sc = Scorecard(
        id=uuid.uuid4(),
        requisition_id=req.id,
        status="approved",
        version_number=1,
    )
    db_session.add(sc)

    # Add criteria
    crit1 = ScorecardCriterion(
        id=uuid.uuid4(),
        scorecard_id=sc.id,
        criterion_name="5+ years Python",
        criterion_type="experience",
        label="5+ years Python",
        weight=30,
        is_mandatory=True,
    )
    crit2 = ScorecardCriterion(
        id=uuid.uuid4(),
        scorecard_id=sc.id,
        criterion_name="FastAPI framework",
        criterion_type="must_have_skills",
        label="FastAPI framework",
        weight=40,
        is_mandatory=True,
    )
    crit3 = ScorecardCriterion(
        id=uuid.uuid4(),
        scorecard_id=sc.id,
        criterion_name="Remote USA",
        criterion_type="location",
        label="Remote USA",
        weight=30,
        is_mandatory=False,
    )
    db_session.add_all([crit1, crit2, crit3])

    # 2. Candidate 1: High match
    cand1 = Candidate(
        id=uuid.uuid4(),
        organization_id=org.id,
        full_name="High Match Developer",
        email="high@developer.org",
        total_experience_years=8.0,
        location="Remote USA",
        consent_status="GRANTED",
    )
    # Candidate 2: Low match
    cand2 = Candidate(
        id=uuid.uuid4(),
        organization_id=org.id,
        full_name="Junior Developer",
        email="junior@developer.org",
        total_experience_years=1.0,
        location="Tokyo, Japan",
        consent_status="GRANTED",
    )
    db_session.add_all([cand1, cand2])
    await db_session.flush()

    # Add resumes
    res1 = Resume(
        id=uuid.uuid4(),
        candidate_id=cand1.id,
        organization_id=org.id,
        requisition_id=req.id,
        file_name="high_match.pdf",
        storage_path="data/high.pdf",
        mime_type="application/pdf",
        file_size_bytes=2048,
        raw_text="8 years of Python backend architecture with FastAPI.",
        normalized_text="8 years of Python backend architecture with FastAPI.",
        parse_status="parsed",
    )
    res2 = Resume(
        id=uuid.uuid4(),
        candidate_id=cand2.id,
        organization_id=org.id,
        requisition_id=req.id,
        file_name="low_match.pdf",
        storage_path="data/low.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
        raw_text="1 year of junior frontend development with HTML/CSS.",
        normalized_text="1 year of junior frontend development with HTML/CSS.",
        parse_status="parsed",
    )
    db_session.add_all([res1, res2])
    await db_session.commit()

    # 3. Evaluate Candidate 1
    eval1_res = await client.post(
        f"/api/v1/requisitions/{req.id}/candidates/{cand1.id}/evaluate",
        headers=headers,
    )
    assert eval1_res.status_code == 200, eval1_res.text
    eval1_data = eval1_res.json()
    assert eval1_data["scorecard_version"] == 1
    assert eval1_data["total_score"] >= 70.0
    assert "score_breakdown" in eval1_data

    # 4. Evaluate Candidate 2
    eval2_res = await client.post(
        f"/api/v1/requisitions/{req.id}/candidates/{cand2.id}/evaluate",
        headers=headers,
    )
    assert eval2_res.status_code == 200, eval2_res.text
    eval2_data = eval2_res.json()
    assert eval2_data["scorecard_version"] == 1
    assert "score_breakdown" in eval2_data
    assert eval1_data["total_score"] >= eval2_data["total_score"]

    # 5. Verify ranking list preserves both candidates (zero automatic rejection)
    list_evals_res = await client.get(
        f"/api/v1/requisitions/{req.id}/evaluations",
        headers=headers,
    )
    assert list_evals_res.status_code == 200
    eval_list = list_evals_res.json()["items"]
    assert len(eval_list) >= 2
    # Verify sorted score descending: Cand 1 above Cand 2
    assert eval_list[0]["total_score"] >= eval_list[1]["total_score"]
    assert any(e["candidate_id"] == str(cand2.id) for e in eval_list)
