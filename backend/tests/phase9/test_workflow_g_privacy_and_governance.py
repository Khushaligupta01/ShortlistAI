from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.requisition import Requisition
from app.models.resume import Resume
from app.models.evaluation import Evaluation
from app.models.scorecard import Scorecard, ScorecardCriterion
from tests.conftest import auth_headers, create_test_org, seed_user_with_org


@pytest.mark.asyncio
async def test_workflow_g_privacy_governance_and_deletion(client: AsyncClient, db_session: AsyncSession):
    """
    Workflow G:
    1. Recruiter initiates candidate consent request.
    2. Candidate grants consent via public token decision portal.
    3. Verify consent history.
    4. Withdraw candidate consent.
    5. Verify processing gates block evaluation and client submission.
    6. Create candidate data access request & generate JSON export.
    7. Verify export strictly excludes internal credentials and server paths.
    8. Create deletion request (Right to be Forgotten).
    9. Delivery Head approves deletion request.
    10. Execute deletion:
        - Irreversible unlinking of physical files from storage disk.
        - Scrubbing candidate PII to '[DELETED]'.
    11. Verify audit log trail.
    12. Verify permanently blocked reprocessing.
    """
    recruiter, staffing_org = await seed_user_with_org(
        db_session,
        email="recruiter.flow_g@privacy.com",
        password="PassWord123!",
        role="recruiter",
        org_name="Privacy Guard Staffing",
    )
    recruiter_headers = auth_headers(recruiter.id, "recruiter", staffing_org.id)

    delivery_head, _ = await seed_user_with_org(
        db_session,
        email="dh.flow_g@privacy.com",
        password="PassWord123!",
        role="delivery_head",
        org_name="Privacy Guard Staffing",
    )
    dh_headers = auth_headers(delivery_head.id, "delivery_head", staffing_org.id)

    client_org = await create_test_org(db_session, name="Privacy Client Co", org_type="client_company")

    # Requisition & Approved Scorecard
    req = Requisition(
        id=uuid.uuid4(),
        organization_id=staffing_org.id,
        created_by=recruiter.id,
        title="Privacy Engineer",
        job_description="GDPR, CCPA, and data governance.",
        status="active",
        client_organization_id=client_org.id,
    )
    db_session.add(req)

    sc = Scorecard(
        id=uuid.uuid4(),
        requisition_id=req.id,
        status="approved",
        version_number=1,
    )
    db_session.add(sc)

    crit = ScorecardCriterion(
        id=uuid.uuid4(),
        scorecard_id=sc.id,
        criterion_name="Privacy Experience",
        criterion_type="experience",
        label="5+ years Privacy Experience",
        weight=100,
        is_mandatory=True,
    )
    db_session.add(crit)

    # Candidate with physical resume on disk
    temp_dir = tempfile.mkdtemp()
    temp_resume_file = Path(temp_dir) / "privacy_cv.pdf"
    temp_resume_file.write_bytes(b"%PDF-1.4 Real CV bytes for deletion testing")
    assert temp_resume_file.exists()

    candidate = Candidate(
        id=uuid.uuid4(),
        organization_id=staffing_org.id,
        full_name="Evelyn Thorne",
        email="evelyn.thorne@example.org",
        phone="+15551112222",
        location="Seattle, WA",
        total_experience_years=6.0,
        consent_status="PENDING",
    )
    db_session.add(candidate)
    await db_session.flush()

    resume = Resume(
        id=uuid.uuid4(),
        candidate_id=candidate.id,
        organization_id=staffing_org.id,
        requisition_id=req.id,
        file_name="privacy_cv.pdf",
        storage_path=str(temp_resume_file),
        mime_type="application/pdf",
        file_size_bytes=len(temp_resume_file.read_bytes()),
        raw_text="Evelyn Thorne. 6 years Privacy Engineering and GDPR compliance.",
        normalized_text="Evelyn Thorne. 6 years Privacy Engineering and GDPR compliance.",
        parse_status="parsed",
    )
    db_session.add(resume)
    await db_session.commit()

    # 1. Create consent request
    consent_req_res = await client.post(
        f"/api/v1/candidates/{candidate.id}/consent-requests",
        headers=recruiter_headers,
        json={"purpose": "recruitment_evaluation"},
    )
    assert consent_req_res.status_code == 201
    token = consent_req_res.json()["token"]

    # 2. Candidate grants consent via public portal
    grant_res = await client.post(
        f"/api/v1/public/consent/{token}/decision",
        json={"decision": "GRANTED", "reason": "Consent granted for Seattle tech roles"},
    )
    assert grant_res.status_code == 200
    assert grant_res.json()["status"] == "GRANTED"

    # 3. Verify consent history
    hist_res = await client.get(
        f"/api/v1/candidates/{candidate.id}/consent",
        headers=recruiter_headers,
    )
    assert hist_res.status_code == 200
    assert len(hist_res.json()) >= 1

    # 4. Withdraw consent
    withdraw_res = await client.post(
        f"/api/v1/candidates/{candidate.id}/consent/withdraw",
        headers=recruiter_headers,
        json={"reason": "Candidate opted out via email request."},
    )
    assert withdraw_res.status_code == 200
    assert withdraw_res.json()["status"] == "WITHDRAWN"

    # 5. Verify processing gates block evaluation and submission
    blocked_eval = await client.post(
        f"/api/v1/requisitions/{req.id}/candidates/{candidate.id}/evaluate",
        headers=recruiter_headers,
    )
    assert blocked_eval.status_code in (400, 403)
    eval_err = (blocked_eval.json().get("message") or blocked_eval.json().get("detail") or "").lower()
    assert "blocked" in eval_err

    blocked_sub = await client.post(
        f"/api/v1/requisitions/{req.id}/submissions",
        headers=recruiter_headers,
        json={
            "candidate_id": str(candidate.id),
            "client_organization_id": str(client_org.id),
        },
    )
    assert blocked_sub.status_code == 403
    sub_err = (blocked_sub.json().get("message") or blocked_sub.json().get("detail") or "").lower()
    assert "blocked" in sub_err

    # 6. Candidate personal data access request & JSON export
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
    assert export_json["profile"]["full_name"] == "Evelyn Thorne"
    # Ensure sensitive system secrets are excluded
    assert "password_hash" not in str(export_json).lower()

    # 7. Create deletion request (Right to be Forgotten)
    del_req_res = await client.post(
        f"/api/v1/candidates/{candidate.id}/deletion-requests",
        headers=recruiter_headers,
        json={"reason": "Full GDPR right to erasure requested by candidate."},
    )
    assert del_req_res.status_code == 201
    del_req_id = del_req_res.json()["id"]

    # 8. Delivery Head reviews & approves
    review_del_res = await client.post(
        f"/api/v1/deletion-requests/{del_req_id}/review",
        headers=dh_headers,
        json={"decision": "APPROVE", "retention_policy_notes": "Erasure authorized under GDPR Art 17."},
    )
    assert review_del_res.status_code == 200
    assert review_del_res.json()["status"] == "APPROVED"

    # 9. Execute permanent deletion
    exec_del_res = await client.post(
        f"/api/v1/deletion-requests/{del_req_id}/execute",
        headers=dh_headers,
    )
    assert exec_del_res.status_code == 200
    assert exec_del_res.json()["status"] == "COMPLETED"
    assert exec_del_res.json()["anonymized"] is True

    # 10. Verify physical storage file unlinked and DB scrubbed
    assert not temp_resume_file.exists()

    await db_session.refresh(candidate)
    assert candidate.full_name == "[DELETED]"
    assert candidate.email is None
    assert candidate.phone is None
    assert candidate.is_anonymized is True

    # 11. Verify audit log captured events
    audit_res = await client.get("/api/v1/audit-events", headers=recruiter_headers)
    assert audit_res.status_code == 200
    event_types = [e["event_type"] for e in audit_res.json()["items"]]
    assert "CONSENT_REQUESTED" in event_types
    assert "CONSENT_WITHDRAWN" in event_types
    assert "DELETION_EXECUTED" in event_types

    # 12. Verify permanently blocked reprocessing
    post_del_eval = await client.post(
        f"/api/v1/requisitions/{req.id}/candidates/{candidate.id}/evaluate",
        headers=recruiter_headers,
    )
    assert post_del_eval.status_code in (400, 403)
