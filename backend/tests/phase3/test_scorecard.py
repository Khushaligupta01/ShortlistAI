from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import (
    auth_headers,
    create_membership,
    create_test_org,
    create_test_user,
)


@pytest.fixture
async def setup_test_data(db_session: AsyncSession):
    """Seed test orgs and users for recruiter and client roles with unique emails."""
    uid = uuid.uuid4().hex[:8]
    org_a = await create_test_org(db_session, name=f"Org A Staffing {uid}", org_type="staffing_firm")
    org_b = await create_test_org(db_session, name=f"Org B Staffing {uid}", org_type="staffing_firm")
    client_org = await create_test_org(db_session, name=f"Acme Client {uid}", org_type="client_company")

    # Recruiter A in Org A
    recruiter_a = await create_test_user(
        db_session, email=f"recruiter_a_{uid}@test.com", display_name="Recruiter A"
    )
    await create_membership(db_session, recruiter_a.id, org_a.id, "recruiter")

    # Recruiter B in Org B
    recruiter_b = await create_test_user(
        db_session, email=f"recruiter_b_{uid}@test.com", display_name="Recruiter B"
    )
    await create_membership(db_session, recruiter_b.id, org_b.id, "recruiter")

    # Client Hiring Manager in client org
    client_user = await create_test_user(
        db_session, email=f"client_hm_{uid}@test.com", display_name="Client HM"
    )
    await create_membership(db_session, client_user.id, client_org.id, "client_hiring_manager")

    headers_recruiter_a = auth_headers(recruiter_a.id, "recruiter", org_a.id)
    headers_recruiter_b = auth_headers(recruiter_b.id, "recruiter", org_b.id)
    headers_client = auth_headers(client_user.id, "client_hiring_manager", client_org.id)

    return {
        "org_a": org_a,
        "org_b": org_b,
        "recruiter_a": recruiter_a,
        "recruiter_b": recruiter_b,
        "client_user": client_user,
        "headers_recruiter_a": headers_recruiter_a,
        "headers_recruiter_b": headers_recruiter_b,
        "headers_client": headers_client,
    }


# ── Scorecard Test Cases (1-10) ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_01_scorecard_creation(client: AsyncClient, setup_test_data):
    """Test 1: Scorecard creation persists with structured fields and criteria."""
    h_a = setup_test_data["headers_recruiter_a"]

    # 1. Create requisition
    req_resp = await client.post(
        "/api/v1/requisitions",
        headers=h_a,
        json={
            "title": "Senior Java Developer",
            "job_description": "We need a Senior Java Developer with Spring Boot and 5-8 years experience in Noida.",
            "location": "Noida",
        },
    )
    assert req_resp.status_code == 201
    req_id = req_resp.json()["id"]

    # 2. Create scorecard
    sc_payload = {
        "experience_min": 5,
        "experience_max": 8,
        "location": "Noida",
        "max_notice_days": 60,
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
                "criterion_name": "Java",
                "normalized_name": "java",
                "label": "Java Development",
                "description": "5+ years of Java",
                "weight": 20,
                "is_mandatory": True,
                "evidence_from_jd": "Strong Java development required",
                "display_order": 0,
            },
            {
                "criterion_type": "must_have_skill",
                "criterion_name": "Spring Boot",
                "normalized_name": "spring_boot",
                "label": "Spring Boot Framework",
                "description": "Hands on Spring Boot",
                "weight": 20,
                "is_mandatory": True,
                "evidence_from_jd": "Hands-on Spring Boot experience",
                "display_order": 1,
            },
        ],
    }

    sc_resp = await client.post(
        f"/api/v1/requisitions/{req_id}/scorecards",
        headers=h_a,
        json=sc_payload,
    )
    assert sc_resp.status_code == 201
    sc_data = sc_resp.json()
    assert sc_data["status"] == "draft"
    assert sc_data["version_number"] == 1
    assert sc_data["experience_min"] == 5
    assert sc_data["experience_max"] == 8
    assert sc_data["location"] == "Noida"
    assert sc_data["max_notice_days"] == 60
    assert len(sc_data["criteria"]) == 2


@pytest.mark.asyncio
async def test_02_scorecard_editing(client: AsyncClient, setup_test_data):
    """Test 2: Recruiter can edit draft scorecard criteria and scoring configuration."""
    h_a = setup_test_data["headers_recruiter_a"]

    req_resp = await client.post(
        "/api/v1/requisitions",
        headers=h_a,
        json={
            "title": "Backend Engineer",
            "job_description": "Backend engineer role description with at least ten characters.",
        },
    )
    req_id = req_resp.json()["id"]

    await client.post(
        f"/api/v1/requisitions/{req_id}/scorecards",
        headers=h_a,
        json={
            "experience_min": 3,
            "criteria": [
                {
                    "criterion_type": "must_have_skill",
                    "criterion_name": "Python",
                    "label": "Python",
                    "weight": 30,
                    "is_mandatory": True,
                    "display_order": 0,
                }
            ],
        },
    )

    # Edit scorecard
    update_payload = {
        "experience_min": 4,
        "experience_max": 7,
        "location": "Bengaluru",
        "max_notice_days": 30,
        "criteria": [
            {
                "criterion_type": "must_have_skill",
                "criterion_name": "Python",
                "label": "Python",
                "weight": 35,
                "is_mandatory": True,
                "display_order": 0,
            },
            {
                "criterion_type": "nice_to_have_skill",
                "criterion_name": "FastAPI",
                "label": "FastAPI",
                "weight": 10,
                "is_mandatory": False,
                "display_order": 1,
            },
        ],
    }

    put_resp = await client.put(
        f"/api/v1/requisitions/{req_id}/scorecard",
        headers=h_a,
        json=update_payload,
    )
    assert put_resp.status_code == 200
    updated = put_resp.json()
    assert updated["experience_min"] == 4
    assert updated["experience_max"] == 7
    assert updated["location"] == "Bengaluru"
    assert updated["max_notice_days"] == 30
    assert len(updated["criteria"]) == 2


@pytest.mark.asyncio
async def test_03_invalid_weights(client: AsyncClient, setup_test_data):
    """Test 3: Negative weights or out-of-range weights are rejected with 422."""
    h_a = setup_test_data["headers_recruiter_a"]

    req_resp = await client.post(
        "/api/v1/requisitions",
        headers=h_a,
        json={"title": "Dev Role", "job_description": "Valid job description for software dev."},
    )
    req_id = req_resp.json()["id"]

    # Negative weight on scoring config
    bad_payload = {
        "scoring_config": {
            "experience": -10,  # Negative
            "must_have_skills": 60,
            "notice_period": 20,
            "location": 20,
            "nice_to_have_skills": 10,
        },
    }
    resp = await client.post(f"/api/v1/requisitions/{req_id}/scorecards", headers=h_a, json=bad_payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_04_weight_total_validation(client: AsyncClient, setup_test_data):
    """Test 4: Scoring config weights must sum to exactly 100."""
    h_a = setup_test_data["headers_recruiter_a"]

    req_resp = await client.post(
        "/api/v1/requisitions",
        headers=h_a,
        json={"title": "Tester Role", "job_description": "Valid job description for QA engineer."},
    )
    req_id = req_resp.json()["id"]

    # Sum is 110 != 100
    invalid_sum = {
        "scoring_config": {
            "experience": 40,
            "must_have_skills": 40,
            "notice_period": 10,
            "location": 10,
            "nice_to_have_skills": 10,
        },
        "criteria": [],
    }
    resp = await client.post(f"/api/v1/requisitions/{req_id}/scorecards", headers=h_a, json=invalid_sum)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_05_missing_required_fields(client: AsyncClient, setup_test_data):
    """Test 5: Missing required fields in requisition or criteria fail validation."""
    h_a = setup_test_data["headers_recruiter_a"]

    # Requisition missing job_description
    resp1 = await client.post("/api/v1/requisitions", headers=h_a, json={"title": "No JD"})
    assert resp1.status_code == 422

    # Requisition with JD < 10 characters
    resp2 = await client.post("/api/v1/requisitions", headers=h_a, json={"title": "Short", "job_description": "too short"})
    assert resp2.status_code == 422


@pytest.mark.asyncio
async def test_06_draft_status(client: AsyncClient, setup_test_data):
    """Test 6: Newly created scorecards and requisitions default to 'draft' status."""
    h_a = setup_test_data["headers_recruiter_a"]

    req_resp = await client.post(
        "/api/v1/requisitions",
        headers=h_a,
        json={"title": "Draft Req", "job_description": "Valid job description for draft requisition."},
    )
    req_data = req_resp.json()
    assert req_data["status"] == "draft"

    sc_resp = await client.post(
        f"/api/v1/requisitions/{req_data['id']}/scorecards",
        headers=h_a,
        json={"experience_min": 2, "criteria": []},
    )
    assert sc_resp.json()["status"] == "draft"


@pytest.mark.asyncio
async def test_07_approval_and_locking(client: AsyncClient, setup_test_data):
    """Test 7: Approval transitions status to 'approved' and locks scorecard from direct edit."""
    h_a = setup_test_data["headers_recruiter_a"]

    req_resp = await client.post(
        "/api/v1/requisitions",
        headers=h_a,
        json={"title": "Approvable Role", "job_description": "Valid job description for approval test."},
    )
    req_id = req_resp.json()["id"]

    # Create scorecard with criteria
    await client.post(
        f"/api/v1/requisitions/{req_id}/scorecards",
        headers=h_a,
        json={
            "criteria": [
                {
                    "criterion_type": "must_have_skill",
                    "criterion_name": "SQL",
                    "label": "SQL Database",
                    "weight": 40,
                    "is_mandatory": True,
                    "display_order": 0,
                }
            ]
        },
    )

    # Approve
    approve_resp = await client.post(
        f"/api/v1/requisitions/{req_id}/scorecard/approve",
        headers=h_a,
    )
    assert approve_resp.status_code == 200
    approved_sc = approve_resp.json()
    assert approved_sc["status"] == "approved"
    assert approved_sc["approved_at"] is not None

    # Requisition should now be active
    req_check = await client.get(f"/api/v1/requisitions/{req_id}", headers=h_a)
    assert req_check.json()["status"] == "active"

    # Attempting to edit an approved scorecard must return 409 Conflict
    edit_resp = await client.put(
        f"/api/v1/requisitions/{req_id}/scorecard",
        headers=h_a,
        json={"experience_min": 10},
    )
    assert edit_resp.status_code == 409


@pytest.mark.asyncio
async def test_08_version_preservation(client: AsyncClient, setup_test_data):
    """Test 8: Duplicating an approved scorecard creates a new draft version, preserving v1."""
    h_a = setup_test_data["headers_recruiter_a"]

    # Create and approve v1
    req_resp = await client.post(
        "/api/v1/requisitions",
        headers=h_a,
        json={"title": "Versioned Role", "job_description": "Valid job description for versioning test."},
    )
    req_id = req_resp.json()["id"]

    await client.post(
        f"/api/v1/requisitions/{req_id}/scorecards",
        headers=h_a,
        json={
            "experience_min": 5,
            "criteria": [
                {
                    "criterion_type": "must_have_skill",
                    "criterion_name": "Java",
                    "label": "Java",
                    "weight": 40,
                    "is_mandatory": True,
                    "display_order": 0,
                }
            ],
        },
    )
    await client.post(f"/api/v1/requisitions/{req_id}/scorecard/approve", headers=h_a)

    # Duplicate to create v2
    dup_resp = await client.post(
        f"/api/v1/requisitions/{req_id}/scorecard/duplicate",
        headers=h_a,
    )
    assert dup_resp.status_code == 201
    v2_sc = dup_resp.json()
    assert v2_sc["version_number"] == 2
    assert v2_sc["status"] == "draft"

    # v2 is editable
    put_v2 = await client.put(
        f"/api/v1/requisitions/{req_id}/scorecard",
        headers=h_a,
        json={"experience_min": 7},
    )
    assert put_v2.status_code == 200
    assert put_v2.json()["experience_min"] == 7
    assert put_v2.json()["version_number"] == 2


@pytest.mark.asyncio
async def test_09_unauthorized_modification_rejected(client: AsyncClient, setup_test_data):
    """Test 9: Client hiring managers are forbidden from creating, updating, or approving scorecards."""
    h_a = setup_test_data["headers_recruiter_a"]
    h_client = setup_test_data["headers_client"]

    req_resp = await client.post(
        "/api/v1/requisitions",
        headers=h_a,
        json={"title": "Auth Test Role", "job_description": "Valid job description for auth test."},
    )
    req_id = req_resp.json()["id"]

    # Client tries to create requisition
    c_create_req = await client.post(
        "/api/v1/requisitions",
        headers=h_client,
        json={"title": "Hacked", "job_description": "Should fail because role is client."},
    )
    assert c_create_req.status_code == 403

    # Client tries to create scorecard
    c_create_sc = await client.post(
        f"/api/v1/requisitions/{req_id}/scorecards",
        headers=h_client,
        json={"experience_min": 3, "criteria": []},
    )
    assert c_create_sc.status_code == 403

    # Client tries to update scorecard
    c_update_sc = await client.put(
        f"/api/v1/requisitions/{req_id}/scorecard",
        headers=h_client,
        json={"experience_min": 5},
    )
    assert c_update_sc.status_code == 403

    # Client tries to approve scorecard
    c_approve_sc = await client.post(
        f"/api/v1/requisitions/{req_id}/scorecard/approve",
        headers=h_client,
    )
    assert c_approve_sc.status_code == 403


@pytest.mark.asyncio
async def test_10_cross_organization_access(client: AsyncClient, setup_test_data):
    """Test 10: Recruiter from Org B cannot access or modify Org A's requisition (returns 404)."""
    h_a = setup_test_data["headers_recruiter_a"]
    h_b = setup_test_data["headers_recruiter_b"]

    # Org A creates a requisition
    req_resp = await client.post(
        "/api/v1/requisitions",
        headers=h_a,
        json={"title": "Secret Org A Role", "job_description": "Confidential JD inside organization A."},
    )
    req_id = req_resp.json()["id"]

    # Recruiter B tries to get Org A requisition -> 404
    b_get = await client.get(f"/api/v1/requisitions/{req_id}", headers=h_b)
    assert b_get.status_code == 404

    # Recruiter B tries to get Org A scorecard -> 404
    b_get_sc = await client.get(f"/api/v1/requisitions/{req_id}/scorecard", headers=h_b)
    assert b_get_sc.status_code == 404

    # Recruiter B tries to update Org A scorecard -> 404
    b_put_sc = await client.put(
        f"/api/v1/requisitions/{req_id}/scorecard",
        headers=h_b,
        json={"experience_min": 2},
    )
    assert b_put_sc.status_code == 404
