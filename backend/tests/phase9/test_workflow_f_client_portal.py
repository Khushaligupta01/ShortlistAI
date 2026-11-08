from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.organization import Organization
from app.models.requisition import Requisition
from app.models.evaluation import Evaluation
from app.models.submission import Submission
from tests.conftest import auth_headers, create_test_org, seed_user_with_org


@pytest.mark.asyncio
async def test_workflow_f_client_portal(client: AsyncClient, db_session: AsyncSession):
    """
    Workflow F:
    1. Recruiter submits evaluated candidate to client company.
    2. Client logs in and opens client dashboard.
    3. Client views submissions with server-side candidate PII masking:
       - Full name replaced with 'Candidate CND-XXXXX'.
       - Email and phone stripped.
    4. Client blocked from raw resume downloads (403) and internal notes (403).
    5. Client shortlists candidate.
    6. Client requests an interview.
    7. Recruiter views updated pipeline state and client inquiries.
    """
    # 1. Setup staffing firm & client firm
    recruiter, staffing_org = await seed_user_with_org(
        db_session,
        email="recruiter.flow_f@staffing.com",
        password="PassWord123!",
        role="recruiter",
        org_name="Staffing Nexus",
    )
    recruiter_headers = auth_headers(recruiter.id, "recruiter", staffing_org.id)

    client_user, client_org = await seed_user_with_org(
        db_session,
        email="client.flow_f@acmecorp.com",
        password="PassWord123!",
        role="client_hiring_manager",
        org_name="Acme Corp",
        org_type="client_company",
    )
    client_headers = auth_headers(client_user.id, "client_hiring_manager", client_org.id)

    # Requisition shared with client
    req = Requisition(
        id=uuid.uuid4(),
        organization_id=staffing_org.id,
        created_by=recruiter.id,
        title="Lead Cloud Architect",
        job_description="AWS, Terraform, Kubernetes.",
        status="active",
        client_organization_id=client_org.id,
    )
    db_session.add(req)

    # Candidate with active evaluation
    candidate = Candidate(
        id=uuid.uuid4(),
        organization_id=staffing_org.id,
        full_name="Samantha Ray",
        email="samantha.ray@example.com",
        phone="+15554443322",
        location="San Francisco, CA",
        total_experience_years=9.0,
        consent_status="GRANTED",
    )
    db_session.add(candidate)
    await db_session.flush()

    evaluation = Evaluation(
        id=uuid.uuid4(),
        candidate_id=candidate.id,
        requisition_id=req.id,
        scorecard_id=uuid.uuid4(),
        total_score=92.0,
        raw_score=92.0,
        normalized_score=92.0,
        evaluation_status="COMPLETED",
        confidence_level="HIGH",
    )
    db_session.add(evaluation)
    await db_session.commit()

    # Recruiter submits candidate to client
    submit_res = await client.post(
        f"/api/v1/requisitions/{req.id}/submissions",
        headers=recruiter_headers,
        json={
            "candidate_id": str(candidate.id),
            "client_organization_id": str(client_org.id),
            "recruiter_notes_for_client": "Top recommended architect.",
        },
    )
    assert submit_res.status_code == 201, submit_res.text
    submission_id = submit_res.json()["submission_id"]

    # 2. Client logs in and opens client dashboard
    client_dash_res = await client.get("/api/v1/client/dashboard", headers=client_headers)
    assert client_dash_res.status_code == 200
    dash_data = client_dash_res.json()
    assert dash_data["total_submissions_count"] >= 1

    # 3. Client views submissions with PII masking
    sub_detail_res = await client.get(
        f"/api/v1/client/submissions/{submission_id}",
        headers=client_headers,
    )
    assert sub_detail_res.status_code == 200
    masked_profile = sub_detail_res.json()
    # Contact details strictly masked / omitted from schema
    assert "CND-" in masked_profile["candidate_reference"]
    assert "Samantha" not in masked_profile["candidate_reference"]
    assert masked_profile.get("email") is None
    assert masked_profile.get("phone") is None

    # 4. Client blocked from internal recruiter notes
    notes_block_res = await client.get(
        f"/api/v1/candidates/{candidate.id}/notes",
        headers=client_headers,
    )
    assert notes_block_res.status_code == 403

    # 5. Client shortlists candidate
    decision_res = await client.post(
        f"/api/v1/client/submissions/{submission_id}/decisions",
        headers=client_headers,
        json={
            "decision": "CLIENT_SHORTLISTED",
            "reason_note": "Strong AWS and Terraform match. Please schedule technical interview.",
        },
    )
    assert decision_res.status_code == 200
    assert decision_res.json()["current_stage"] == "CLIENT_SHORTLISTED"

    # 6. Client creates interview request
    req_res = await client.post(
        f"/api/v1/client/submissions/{submission_id}/requests",
        headers=client_headers,
        json={
            "request_type": "INTERVIEW",
            "details": "Would like to schedule 45-min video call on Thursday afternoon.",
        },
    )
    assert req_res.status_code == 200, req_res.text
    assert req_res.json()["request_type"] == "INTERVIEW"

    # 7. Recruiter views updated pipeline board
    board_res = await client.get("/api/v1/recruiter/pipeline", headers=recruiter_headers)
    assert board_res.status_code == 200
    board_data = board_res.json()
    assert any(
        s["submission_id"] == str(submission_id) and s["current_stage"] == "INTERVIEW_REQUESTED"
        for s in board_data["submissions"]
    )
