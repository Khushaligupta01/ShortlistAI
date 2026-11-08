from __future__ import annotations

import json
import tempfile
import uuid
from pathlib import Path
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.candidate import Candidate, CandidateSkill, CandidateEmployment
from app.models.organization import Organization
from app.models.requisition import Requisition
from app.models.scorecard import Scorecard
from app.models.resume import Resume
from app.models.evaluation import Evaluation
from tests.conftest import auth_headers, create_test_org, seed_user_with_org


@pytest.mark.asyncio
async def test_phase8_full_privacy_lifecycle_e2e(client: AsyncClient, db_session: AsyncSession):
    # 1. Setup Staffing Org with Recruiter and Delivery Head
    recruiter, staffing_org = await seed_user_with_org(
        db_session, email="rec_e2e@staffing.com", password="Password123!", role="recruiter", org_name="E2E Staffing Inc"
    )
    recruiter_headers = auth_headers(recruiter.id, "recruiter", staffing_org.id)

    delivery_head, _ = await seed_user_with_org(
        db_session, email="head_e2e@staffing.com", password="Password123!", role="delivery_head", org_name="E2E Staffing Inc"
    )
    dh_headers = auth_headers(delivery_head.id, "delivery_head", staffing_org.id)

    # Setup Client Org
    client_org = await create_test_org(db_session, name="E2E Client Target", org_type="client_company")

    # Create Requisition shared with client
    req = Requisition(
        id=uuid.uuid4(),
        organization_id=staffing_org.id,
        created_by=recruiter.id,
        title="Principal AI Governance Architect",
        job_description="Experience with responsible AI, data privacy, and ethical ML architectures.",
        status="active",
        client_organization_id=client_org.id,
    )
    db_session.add(req)

    # Create Scorecard
    sc = Scorecard(
        id=uuid.uuid4(),
        requisition_id=req.id,
        status="approved",
        version_number=1,
    )
    db_session.add(sc)

    # Create Candidate initially with PENDING consent
    candidate = Candidate(
        id=uuid.uuid4(),
        organization_id=staffing_org.id,
        full_name="Dr. Aris Thorne",
        email="aris.thorne@example.org",
        phone="+15550001111",
        location="Boston, MA",
        total_experience_years=12.0,
        consent_status="PENDING",
    )
    db_session.add(candidate)
    await db_session.flush()

    # Create physical resume file in tempdir
    temp_dir = tempfile.mkdtemp()
    temp_resume_file = Path(temp_dir) / "dr_thorne_resume.pdf"
    temp_resume_file.write_bytes(b"%PDF-1.4 Aris Thorne AI Governance and Privacy Engineer CV")
    assert temp_resume_file.exists()

    resume = Resume(
        id=uuid.uuid4(),
        candidate_id=candidate.id,
        organization_id=staffing_org.id,
        requisition_id=req.id,
        file_name="dr_thorne_resume.pdf",
        storage_path=str(temp_resume_file),
        mime_type="application/pdf",
        file_size_bytes=len(temp_resume_file.read_bytes()),
        raw_text="Dr. Aris Thorne. 12 years of AI Governance, Privacy Engineering, and Ethical ML.",
        normalized_text="Dr. Aris Thorne. 12 years of AI Governance, Privacy Engineering, and Ethical ML.",
        parse_status="parsed",
    )
    db_session.add(resume)
    await db_session.commit()

    # Step 1: Recruiter creates consent request
    consent_req_res = await client.post(
        f"/api/v1/candidates/{candidate.id}/consent-requests",
        headers=recruiter_headers,
        json={"purpose": "ai_recruitment_screening"},
    )
    assert consent_req_res.status_code == 201
    raw_token = consent_req_res.json()["token"]

    # Step 2 & 3: Candidate visits public link & grants consent
    pub_info_res = await client.get(f"/api/v1/public/consent/{raw_token}")
    assert pub_info_res.status_code == 200
    assert pub_info_res.json()["is_valid"] is True

    grant_res = await client.post(
        f"/api/v1/public/consent/{raw_token}/decision",
        json={"decision": "GRANTED", "reason": "Authorized for AI roles"},
    )
    assert grant_res.status_code == 200
    assert grant_res.json()["status"] == "GRANTED"

    await db_session.refresh(candidate)
    assert candidate.consent_status == "GRANTED"

    # Step 4: Recruiter evaluates candidate
    eval_res = await client.post(
        f"/api/v1/requisitions/{req.id}/candidates/{candidate.id}/evaluate",
        headers=recruiter_headers,
    )
    assert eval_res.status_code == 200, eval_res.text
    evaluation_id = eval_res.json()["id"]

    # Step 5: Candidate withdraws consent
    withdraw_res = await client.post(
        f"/api/v1/candidates/{candidate.id}/consent/withdraw",
        headers=recruiter_headers,
        json={"reason": "Candidate withdrew authorization on 2026-11-08."},
    )
    assert withdraw_res.status_code == 200
    assert withdraw_res.json()["status"] == "WITHDRAWN"

    await db_session.refresh(candidate)
    assert candidate.consent_status == "WITHDRAWN"

    # Step 6: Processing blocked according to policy
    blocked_eval_res = await client.post(
        f"/api/v1/requisitions/{req.id}/candidates/{candidate.id}/evaluate",
        headers=recruiter_headers,
    )
    assert blocked_eval_res.status_code in (400, 403)
    err_eval = (blocked_eval_res.json().get("message") or blocked_eval_res.json().get("detail") or "").lower()
    assert "blocked" in err_eval

    blocked_sub_res = await client.post(
        f"/api/v1/requisitions/{req.id}/submissions",
        headers=recruiter_headers,
        json={
            "candidate_id": str(candidate.id),
            "client_organization_id": str(client_org.id),
        },
    )
    assert blocked_sub_res.status_code == 403
    err_sub = (blocked_sub_res.json().get("message") or blocked_sub_res.json().get("detail") or "").lower()
    assert "blocked" in err_sub

    # Step 7 & 8: Data access request created & exported
    data_req_res = await client.post(
        f"/api/v1/candidates/{candidate.id}/data-requests",
        headers=recruiter_headers,
        json={"request_type": "EXPORT"},
    )
    assert data_req_res.status_code == 201
    data_request_id = data_req_res.json()["id"]

    export_res = await client.post(
        f"/api/v1/data-requests/{data_request_id}/export",
        headers=recruiter_headers,
    )
    assert export_res.status_code == 200
    export_json = export_res.json()
    assert export_json["profile"]["full_name"] == "Dr. Aris Thorne"
    assert export_json["profile"]["consent_status"] == "WITHDRAWN"

    # Step 9: Candidate deletion request is created
    del_req_res = await client.post(
        f"/api/v1/candidates/{candidate.id}/deletion-requests",
        headers=recruiter_headers,
        json={"reason": "Candidate requested full GDPR right to erasure."},
    )
    assert del_req_res.status_code == 201
    del_req_id = del_req_res.json()["id"]

    # Step 10: Authorized Delivery Head approves deletion
    del_review_res = await client.post(
        f"/api/v1/deletion-requests/{del_req_id}/review",
        headers=dh_headers,
        json={"decision": "APPROVE", "retention_policy_notes": "No legal holds active; proceed with full wipe."},
    )
    assert del_review_res.status_code == 200
    assert del_review_res.json()["status"] == "APPROVED"

    # Step 11 & 12: Controlled deletion execution
    del_exec_res = await client.post(
        f"/api/v1/deletion-requests/{del_req_id}/execute",
        headers=dh_headers,
    )
    assert del_exec_res.status_code == 200
    assert del_exec_res.json()["status"] == "COMPLETED"
    assert del_exec_res.json()["anonymized"] is True

    # Physical file on storage disk must be deleted
    assert not temp_resume_file.exists()

    # Candidate record anonymized
    await db_session.refresh(candidate)
    assert candidate.full_name == "[DELETED]"
    assert candidate.email is None
    assert candidate.phone is None
    assert candidate.location == "[DELETED]"
    assert candidate.is_anonymized is True
    assert candidate.deletion_status == "COMPLETED"

    # Step 13: Audit history records the trail
    audit_res = await client.get("/api/v1/audit-events", headers=recruiter_headers)
    assert audit_res.status_code == 200
    event_types = [e["event_type"] for e in audit_res.json()["items"]]
    assert "CONSENT_REQUESTED" in event_types
    assert "CONSENT_GRANTED" in event_types
    assert "CONSENT_WITHDRAWN" in event_types
    assert "DELETION_REQUESTED" in event_types
    assert "DELETION_REVIEWED" in event_types
    assert "DELETION_EXECUTED" in event_types

    # Step 14: Reprocessing and submissions permanently prevented
    fail_eval = await client.post(
        f"/api/v1/requisitions/{req.id}/candidates/{candidate.id}/evaluate",
        headers=recruiter_headers,
    )
    assert fail_eval.status_code in (400, 403)
    fail_err = (fail_eval.json().get("message") or fail_eval.json().get("detail") or "").lower()
    assert "deleted" in fail_err or "blocked" in fail_err
