from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import auth_headers, seed_user_with_org


@pytest.mark.asyncio
async def test_workflow_b_jd_and_scorecard_lifecycle(client: AsyncClient, db_session: AsyncSession):
    """
    Workflow B:
    1. Create a requisition with realistic job description.
    2. Attempt to create scorecard with invalid weights (sum != 100) -> expects 422/400 validation error.
    3. Create scorecard with valid weights totaling exactly 100.
    4. Edit/update draft scorecard criteria.
    5. Approve scorecard -> locks to 'approved' status.
    6. Verify modifications to approved scorecard are rejected with conflict error.
    7. Verify version persistence.
    """
    recruiter, org = await seed_user_with_org(
        db_session,
        email="recruiter.jd@example.com",
        password="PassWord123!",
        role="recruiter",
        org_name="TechStaff Agency",
    )
    headers = auth_headers(recruiter.id, "recruiter", org.id)

    # 1. Create requisition
    jd_text = (
        "We are seeking a Senior Python Engineer to architect high-throughput APIs.\n"
        "Requirements:\n"
        "- 5+ years of Python software development experience.\n"
        "- Production experience with FastAPI and PostgreSQL.\n"
        "- Docker and Kubernetes container orchestration.\n"
        "- Location: Austin, TX or Remote.\n"
        "- Notice period: Notice period up to 30 days."
    )
    create_req_res = await client.post(
        "/api/v1/requisitions",
        headers=headers,
        json={
            "title": "Senior Python Backend Engineer",
            "job_description": jd_text,
            "location": "Austin, TX",
        },
    )
    assert create_req_res.status_code == 201, create_req_res.text
    req_data = create_req_res.json()
    req_id = req_data["id"]
    assert req_data["title"] == "Senior Python Backend Engineer"

    # 2. Total weight validation: sum != 100 must fail with 422
    invalid_scorecard_payload = {
        "scoring_config": {
            "experience": 40,
            "must_have_skills": 40,
            "notice_period": 10,
            "location": 10,
            "nice_to_have_skills": 10,  # sum = 110 != 100
        },
        "criteria": [
            {
                "criterion_type": "experience",
                "criterion_name": "Python Experience",
                "label": "5+ years Python",
                "weight": 30,
                "is_mandatory": True,
            },
        ],
    }
    invalid_res = await client.post(
        f"/api/v1/requisitions/{req_id}/scorecards",
        headers=headers,
        json=invalid_scorecard_payload,
    )
    assert invalid_res.status_code == 422

    # 3. Create valid scorecard (Scoring config sum = 100)
    valid_scorecard_payload = {
        "experience_min": 5,
        "location": "Austin, TX",
        "max_notice_days": 30,
        "scoring_config": {
            "experience": 30,
            "must_have_skills": 40,
            "notice_period": 15,
            "location": 10,
            "nice_to_have_skills": 5,
        },
        "criteria": [
            {
                "criterion_type": "must_have_skill",
                "criterion_name": "Python",
                "normalized_name": "python",
                "label": "Python",
                "weight": 20,
                "is_mandatory": True,
                "display_order": 0,
            },
            {
                "criterion_type": "must_have_skill",
                "criterion_name": "FastAPI",
                "normalized_name": "fastapi",
                "label": "FastAPI Framework",
                "weight": 20,
                "is_mandatory": True,
                "display_order": 1,
            },
        ],
    }
    sc_res = await client.post(
        f"/api/v1/requisitions/{req_id}/scorecards",
        headers=headers,
        json=valid_scorecard_payload,
    )
    assert sc_res.status_code == 201, sc_res.text
    sc_data = sc_res.json()
    assert sc_data["status"] == "draft"
    assert sc_data["version_number"] == 1
    assert len(sc_data["criteria"]) == 2

    # 4. Edit draft scorecard
    update_res = await client.put(
        f"/api/v1/requisitions/{req_id}/scorecard",
        headers=headers,
        json=valid_scorecard_payload,
    )
    assert update_res.status_code == 200, update_res.text

    # 5. Approve scorecard
    approve_res = await client.post(
        f"/api/v1/requisitions/{req_id}/scorecard/approve",
        headers=headers,
    )
    assert approve_res.status_code == 200, approve_res.text
    approved_data = approve_res.json()
    assert approved_data["status"] == "approved"
    assert approved_data["approved_at"] is not None

    # 6. Verify modifications to approved scorecard fail with conflict
    conflict_res = await client.put(
        f"/api/v1/requisitions/{req_id}/scorecard",
        headers=headers,
        json=valid_scorecard_payload,
    )
    assert conflict_res.status_code in (400, 409)

    # 7. Verify version persistence
    get_sc_res = await client.get(
        f"/api/v1/requisitions/{req_id}/scorecard",
        headers=headers,
    )
    assert get_sc_res.status_code == 200
    persisted = get_sc_res.json()
    assert persisted["status"] == "approved"
    assert persisted["version_number"] == 1
