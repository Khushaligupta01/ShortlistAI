from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.candidate import Candidate
from app.models.organization import Organization
from app.models.requisition import Requisition
from app.models.scorecard import Scorecard
from app.models.evaluation import Evaluation
from app.models.resume import Resume
from app.services.consent_service import withdraw_candidate_consent
from tests.conftest import auth_headers, create_test_org, seed_user_with_org


@pytest.mark.asyncio
async def test_evaluation_blocked_when_consent_withdrawn(client: AsyncClient, db_session: AsyncSession):
    # Setup Staffing Org & Recruiter
    recruiter, org = await seed_user_with_org(
        db_session, email="rec_eval_block@staffing.com", password="Password123!", role="recruiter", org_name="Consent Block Org"
    )
    recruiter_headers = auth_headers(recruiter.id, "recruiter", org.id)

    # Requisition
    req = Requisition(
        id=uuid.uuid4(),
        organization_id=org.id,
        created_by=recruiter.id,
        title="Full Stack Python Engineer",
        job_description="Python, FastAPI, Next.js required.",
        status="active",
    )
    db_session.add(req)
    await db_session.commit()

    # Scorecard
    sc = Scorecard(
        id=uuid.uuid4(),
        requisition_id=req.id,
        status="approved",
        version_number=1,
    )
    db_session.add(sc)

    # Candidate with WITHDRAWN consent
    candidate = Candidate(
        id=uuid.uuid4(),
        organization_id=org.id,
        full_name="Blocked Candidate",
        email="blocked@example.com",
        consent_status="WITHDRAWN",
    )
    db_session.add(candidate)

    # Resume
    resume = Resume(
        id=uuid.uuid4(),
        candidate_id=candidate.id,
        organization_id=org.id,
        requisition_id=req.id,
        file_name="blocked_resume.pdf",
        storage_path="data/resumes/dummy.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
        raw_text="Experienced Full Stack Python engineer with FastAPI.",
        parse_status="parsed",
    )
    db_session.add(resume)
    await db_session.commit()

    # Attempt to evaluate candidate -> should fail with 400 or ValueError containing "blocked"
    eval_res = await client.post(
        f"/api/v1/requisitions/{req.id}/candidates/{candidate.id}/evaluate",
        headers=recruiter_headers,
    )
    assert eval_res.status_code in (400, 403)
    err_msg = (eval_res.json().get("message") or eval_res.json().get("detail") or "").lower()
    assert "blocked" in err_msg or "consent" in err_msg


@pytest.mark.asyncio
async def test_client_submission_blocked_when_consent_withdrawn(client: AsyncClient, db_session: AsyncSession):
    # Setup Staffing Org & Recruiter
    recruiter, staffing_org = await seed_user_with_org(
        db_session, email="rec_sub_block@staffing.com", password="Password123!", role="recruiter", org_name="Apex Sub Block"
    )
    recruiter_headers = auth_headers(recruiter.id, "recruiter", staffing_org.id)

    # Setup Client Org
    client_org = await create_test_org(db_session, name="Client Sub Block Target", org_type="client_company")

    # Requisition shared with client
    req = Requisition(
        id=uuid.uuid4(),
        organization_id=staffing_org.id,
        created_by=recruiter.id,
        title="DevOps Engineer",
        job_description="Kubernetes, Terraform, AWS.",
        status="active",
        client_organization_id=client_org.id,
    )
    db_session.add(req)

    # Candidate with active evaluation but WITHDRAWN consent
    candidate = Candidate(
        id=uuid.uuid4(),
        organization_id=staffing_org.id,
        full_name="Sarah Connor",
        email="sarah.c@example.com",
        consent_status="WITHDRAWN",
    )
    db_session.add(candidate)
    await db_session.commit()

    evaluation = Evaluation(
        id=uuid.uuid4(),
        candidate_id=candidate.id,
        requisition_id=req.id,
        scorecard_id=uuid.uuid4(),
        total_score=85.0,
        raw_score=85.0,
        normalized_score=85.0,
        evaluation_status="COMPLETED",
        confidence_level="HIGH",
    )
    db_session.add(evaluation)
    await db_session.commit()

    # Recruiter attempts to submit candidate to client -> MUST return 403 Forbidden
    sub_res = await client.post(
        f"/api/v1/requisitions/{req.id}/submissions",
        headers=recruiter_headers,
        json={
            "candidate_id": str(candidate.id),
            "client_organization_id": str(client_org.id),
            "recruiter_notes_for_client": "Top candidate.",
        },
    )
    assert sub_res.status_code == 403, sub_res.text
    err_detail = (sub_res.json().get("message") or sub_res.json().get("detail") or "").lower()
    assert "blocked" in err_detail or "consent" in err_detail
