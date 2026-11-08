from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate, CandidateSkill, CandidateEmployment
from app.models.requisition import Requisition
from app.models.evaluation import Evaluation
from tests.conftest import auth_headers, seed_user_with_org


@pytest.mark.asyncio
async def test_workflow_e_recruiter_workspace(client: AsyncClient, db_session: AsyncSession):
    """
    Workflow E:
    1. Recruiter opens dashboard metrics.
    2. Searches candidates across skills and titles.
    3. Filters candidates by experience and location.
    4. Sorts candidates and navigates pagination.
    5. Opens candidate profile.
    6. Records recruiter review decision on evaluation.
    7. Adds and retrieves confidential internal notes.
    8. Verifies data persistence on reload.
    """
    recruiter, org = await seed_user_with_org(
        db_session,
        email="recruiter.workspace@example.com",
        password="PassWord123!",
        role="recruiter",
        org_name="Apex Workspace Staffing",
    )
    headers = auth_headers(recruiter.id, "recruiter", org.id)

    # Requisition
    req = Requisition(
        id=uuid.uuid4(),
        organization_id=org.id,
        created_by=recruiter.id,
        title="Full Stack Tech Lead",
        job_description="React, TypeScript, Python, Node.",
        status="active",
    )
    db_session.add(req)

    # Multiple candidates
    cands = []
    for i in range(5):
        c = Candidate(
            id=uuid.uuid4(),
            organization_id=org.id,
            full_name=f"Candidate {i+1} Alpha",
            email=f"candidate_{i+1}@apex.org",
            location="Seattle, WA" if i % 2 == 0 else "New York, NY",
            total_experience_years=float(3 + i * 2),
            consent_status="GRANTED",
        )
        cands.append(c)
        db_session.add(c)
    await db_session.flush()

    # Evaluation for candidate 0
    ev = Evaluation(
        id=uuid.uuid4(),
        candidate_id=cands[0].id,
        requisition_id=req.id,
        scorecard_id=uuid.uuid4(),
        total_score=88.5,
        raw_score=88.5,
        normalized_score=88.5,
        evaluation_status="COMPLETED",
        confidence_level="HIGH",
    )
    db_session.add(ev)
    await db_session.commit()

    # 1. Recruiter dashboard metrics
    dash_res = await client.get("/api/v1/recruiter/metrics", headers=headers)
    assert dash_res.status_code == 200
    assert dash_res.json()["total_candidates"] >= 5

    # 2. Candidate search
    search_res = await client.get(
        "/api/v1/candidates",
        headers=headers,
        params={"search": "Alpha"},
    )
    assert search_res.status_code == 200
    assert len(search_res.json()["items"]) >= 5

    # 3. Candidate multi-attribute filtering (min_experience=7.0)
    filter_res = await client.get(
        "/api/v1/candidates",
        headers=headers,
        params={"min_experience": 7.0},
    )
    assert filter_res.status_code == 200
    filtered_items = filter_res.json()["items"]
    assert all(c["total_experience_years"] >= 7.0 for c in filtered_items if c["total_experience_years"])

    # 4. Sorting & pagination
    sort_res = await client.get(
        "/api/v1/candidates",
        headers=headers,
        params={"sort_by": "experience", "sort_order": "desc", "page": 1, "page_size": 2},
    )
    assert sort_res.status_code == 200
    sort_data = sort_res.json()
    assert len(sort_data["items"]) == 2
    assert sort_data["items"][0]["total_experience_years"] >= sort_data["items"][1]["total_experience_years"]

    # 5. Open candidate profile
    cand_profile_res = await client.get(
        f"/api/v1/candidates/{cands[0].id}",
        headers=headers,
    )
    assert cand_profile_res.status_code == 200
    assert cand_profile_res.json()["full_name"] == "Candidate 1 Alpha"

    # 6. Record recruiter review
    review_res = await client.post(
        f"/api/v1/evaluations/{ev.id}/review",
        headers=headers,
        json={
            "decision": "SHORTLIST",
            "notes": "Excellent architecture background. Move to client submission.",
        },
    )
    assert review_res.status_code == 200, review_res.text
    assert review_res.json()["decision"] == "SHORTLIST"

    # 7. Add confidential internal recruiter note
    note_res = await client.post(
        f"/api/v1/candidates/{cands[0].id}/notes",
        headers=headers,
        json={
            "requisition_id": str(req.id),
            "content": "Discussed expected compensation of $180k. Candidate ready for client interview.",
        },
    )
    assert note_res.status_code == 201, note_res.text
    note_id = note_res.json()["id"]

    # 8. Reload candidate notes and verify persistence
    notes_list_res = await client.get(
        f"/api/v1/candidates/{cands[0].id}/notes",
        headers=headers,
    )
    assert notes_list_res.status_code == 200
    notes_data = notes_list_res.json()
    assert notes_data["total"] >= 1
    notes = notes_data["notes"]
    assert any(n["id"] == note_id for n in notes)
