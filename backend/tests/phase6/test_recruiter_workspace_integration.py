from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate, CandidateSkill
from app.models.evaluation import Evaluation
from app.models.requisition import Requisition
from app.models.resume import Resume
from app.models.scorecard import Scorecard, ScorecardCriterion
from tests.conftest import auth_headers, seed_user_with_org


@pytest.mark.asyncio
async def test_recruiter_workspace_end_to_end(client: AsyncClient, db_session: AsyncSession):
    recruiter, org = await seed_user_with_org(
        db_session, email="workspace_e2e@example.com", password="Password123!", role="recruiter"
    )
    headers = auth_headers(recruiter.id, "recruiter", org.id)

    # 1. Recruiter creates Requisition
    req_payload = {
        "title": "Principal Distributed Systems Engineer",
        "job_description": "We need a principal engineer with 10+ years experience in Python, distributed databases, and cloud architecture.",
        "location": "San Francisco, CA",
    }
    req_res = await client.post("/api/v1/requisitions", json=req_payload, headers=headers)
    assert req_res.status_code == 201
    req_data = req_res.json()
    req_id = req_data["id"]

    # 2. Scorecard creation and approval
    sc = Scorecard(
        id=uuid.uuid4(),
        requisition_id=uuid.UUID(req_id),
        status="approved",
        version_number=1,
    )
    db_session.add(sc)
    await db_session.commit()

    crit = ScorecardCriterion(
        id=uuid.uuid4(),
        scorecard_id=sc.id,
        criterion_type="must_have",
        criterion_name="Python",
        label="Python Mastery",
        weight=100,
    )
    db_session.add(crit)
    await db_session.commit()

    # Activate requisition
    req_obj = await db_session.get(Requisition, uuid.UUID(req_id))
    req_obj.status = "active"
    await db_session.commit()

    # 3. Create Candidate & Resume
    cand = Candidate(
        id=uuid.uuid4(),
        organization_id=org.id,
        full_name="Gregory House",
        email="house@princeton.edu",
        location="Princeton, NJ",
        total_experience_years=14.0,
        notice_period_days=15,
    )
    db_session.add(cand)
    await db_session.commit()

    db_session.add(
        CandidateSkill(id=uuid.uuid4(), candidate_id=cand.id, name="python", raw_name="Python")
    )
    resume = Resume(
        id=uuid.uuid4(),
        candidate_id=cand.id,
        organization_id=org.id,
        requisition_id=uuid.UUID(req_id),
        file_name="house_cv.pdf",
        storage_path="/resumes/house_cv.pdf",
        mime_type="application/pdf",
        file_size_bytes=32000,
        parse_status="parsed",
    )
    db_session.add(resume)
    await db_session.commit()

    # 4. Create Evaluation
    ev = Evaluation(
        id=uuid.uuid4(),
        candidate_id=cand.id,
        requisition_id=uuid.UUID(req_id),
        scorecard_id=sc.id,
        organization_id=org.id,
        total_score=94.5,
        raw_score=94.5,
        normalized_score=94.5,
        evidence_coverage=0.98,
        confidence_level="HIGH",
        evaluation_status="COMPLETED",
        is_current=True,
        score_breakdown_json={
            "summary": "Superb diagnostic and distributed engineering problem solving skills",
            "must_have_skills": {"awarded": 100, "max": 100},
        },
    )
    db_session.add(ev)
    await db_session.commit()

    # 5. Recruiter Reviews candidate and marks as SHORTLIST
    review_res = await client.post(
        f"/api/v1/evaluations/{ev.id}/review",
        json={"decision": "SHORTLIST", "notes": "Exceptional problem solver, ready for client delivery."},
        headers=headers,
    )
    assert review_res.status_code == 200
    assert review_res.json()["decision"] == "SHORTLIST"

    # 6. Recruiter records confidential internal note
    note_res = await client.post(
        f"/api/v1/candidates/{cand.id}/notes",
        json={"content": "Candidate expects $240k base + equity. Available in 2 weeks.", "requisition_id": req_id},
        headers=headers,
    )
    assert note_res.status_code == 201

    # 7. Check Dashboard API aggregates
    dash_res = await client.get("/api/v1/recruiter/dashboard", headers=headers)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    metrics = dash_data["metrics"]
    assert metrics["active_requisitions"] == 1
    assert metrics["total_candidates"] == 1
    assert metrics["resumes_processed"] == 1
    assert metrics["completed_evaluations"] == 1
    assert metrics["candidates_shortlisted"] == 1
    assert metrics["candidates_awaiting_review"] == 0

    # Verify recent activity timeline includes recorded actions
    activity_types = [a["type"] for a in dash_data["recent_activity"]]
    assert "requisition_created" in activity_types
    assert "evaluation_completed" in activity_types
    assert "review_recorded" in activity_types
    assert "note_added" in activity_types

    # 8. Check Candidate Search
    cand_search_res = await client.get(
        f"/api/v1/candidates?search=Gregory&review_decision=SHORTLIST",
        headers=headers,
    )
    assert cand_search_res.status_code == 200
    cands = cand_search_res.json()
    assert cands["total"] == 1
    assert cands["items"][0]["full_name"] == "Gregory House"
    assert cands["items"][0]["evaluation_score"] == 94.5
    assert cands["items"][0]["review_decision"] == "SHORTLIST"
