from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.evaluation import Evaluation
from app.models.requisition import Requisition
from app.models.scorecard import Scorecard
from app.models.submission import ClientRequest, PipelineRecord, Submission
from tests.conftest import auth_headers, create_test_org, seed_user_with_org


@pytest.mark.asyncio
async def test_client_decisions_pipeline_transitions_and_requests(client: AsyncClient, db_session: AsyncSession):
    # 1. Setup recruiter and client
    recruiter, staffing_org = await seed_user_with_org(
        db_session, email="rec_dec@staffing.com", password="Password123!", role="recruiter", org_name="Decision Staffing"
    )
    recruiter_headers = auth_headers(recruiter.id, "recruiter", staffing_org.id)

    client_org = await create_test_org(db_session, name="HealthTech Global", org_type="client_company")
    client_user, _ = await seed_user_with_org(
        db_session, email="hm_dec@healthtech.com", password="Password123!", role="client_hiring_manager", org_name="HealthTech Global"
    )
    client_headers = auth_headers(client_user.id, "client_hiring_manager", client_org.id)

    # 2. Requisition, Scorecard, Candidate, and Evaluation
    req = Requisition(
        id=uuid.uuid4(),
        organization_id=staffing_org.id,
        created_by=recruiter.id,
        title="Senior Bioinformatics Engineer",
        job_description="Genomic pipelines and Python.",
        status="active",
        client_organization_id=client_org.id,
    )
    db_session.add(req)
    await db_session.commit()

    sc = Scorecard(
        id=uuid.uuid4(),
        requisition_id=req.id,
        status="approved",
        version_number=1,
    )
    db_session.add(sc)
    await db_session.commit()

    cand = Candidate(
        id=uuid.uuid4(),
        organization_id=staffing_org.id,
        full_name="Rosalind Franklin",
        email="rosalind@crystallography.ac.uk",
        total_experience_years=7.0,
    )
    db_session.add(cand)
    await db_session.commit()

    eval_obj = Evaluation(
        id=uuid.uuid4(),
        candidate_id=cand.id,
        requisition_id=req.id,
        scorecard_id=sc.id,
        scorecard_version=1,
        total_score=91.0,
        raw_score=91.0,
        normalized_score=91.0,
        evaluation_status="completed",
    )
    db_session.add(eval_obj)
    await db_session.commit()

    # Recruiter submits candidate
    sub_res = await client.post(
        f"/api/v1/requisitions/{req.id}/submissions",
        json={"candidate_id": str(cand.id), "client_organization_id": str(client_org.id)},
        headers=recruiter_headers,
    )
    assert sub_res.status_code == 201
    submission_id = sub_res.json()["submission_id"]

    # 3. Test Invalid Decision
    bad_dec = await client.post(
        f"/api/v1/client/submissions/{submission_id}/decisions",
        json={"decision": "HIRED_IMMEDIATELY"},
        headers=client_headers,
    )
    assert bad_dec.status_code == 400

    # 4. Client records INTERVIEW_REQUESTED with details
    intv_res = await client.post(
        f"/api/v1/client/submissions/{submission_id}/decisions",
        json={
            "decision": "INTERVIEW_REQUESTED",
            "reason_note": "Impressive background, fits our genomic team well.",
            "interview_details": "45-min technical interview with Bioinformatics Team on Friday 10am or 2pm.",
        },
        headers=client_headers,
    )
    assert intv_res.status_code == 200
    intv_data = intv_res.json()
    assert intv_data["current_stage"] == "INTERVIEW_REQUESTED"
    assert intv_data["latest_decision"] == "INTERVIEW_REQUESTED"

    # Verify ClientRequest was created
    req_query = await db_session.execute(
        select(ClientRequest).where(ClientRequest.submission_id == uuid.UUID(submission_id))
    )
    requests = req_query.scalars().all()
    assert len(requests) == 1
    assert requests[0].request_type == "INTERVIEW"
    assert "Friday 10am" in requests[0].details
    assert requests[0].status == "PENDING"

    # 5. Client records CLIENT_SHORTLISTED
    short_res = await client.post(
        f"/api/v1/client/submissions/{submission_id}/decisions",
        json={
            "decision": "CLIENT_SHORTLISTED",
            "reason_note": "Confirmed for client shortlist.",
        },
        headers=client_headers,
    )
    assert short_res.status_code == 200
    assert short_res.json()["current_stage"] == "CLIENT_SHORTLISTED"

    # Verify PipelineRecords in order
    history_res = await client.get(
        f"/api/v1/client/submissions/{submission_id}/history",
        headers=client_headers,
    )
    assert history_res.status_code == 200
    history = history_res.json()
    stages = [h["current_stage"] for h in history]
    assert "CLIENT_SHORTLISTED" in stages
    assert "INTERVIEW_REQUESTED" in stages
    assert "SUBMITTED" in stages
