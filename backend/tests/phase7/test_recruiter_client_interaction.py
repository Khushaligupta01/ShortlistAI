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
async def test_recruiter_client_interaction_pipeline_flow(client: AsyncClient, db_session: AsyncSession):
    # 1. Setup recruiter and client
    recruiter, staffing_org = await seed_user_with_org(
        db_session, email="rec_flow@staffing.com", password="Password123!", role="recruiter", org_name="Flow Staffing Partners"
    )
    recruiter_headers = auth_headers(recruiter.id, "recruiter", staffing_org.id)

    client_org = await create_test_org(db_session, name="SkyNet Aerospace", org_type="client_company")
    client_user, _ = await seed_user_with_org(
        db_session, email="hm_skynet@aerospace.com", password="Password123!", role="client_hiring_manager", org_name="SkyNet Aerospace"
    )
    client_headers = auth_headers(client_user.id, "client_hiring_manager", client_org.id)

    # 2. Requisition and candidate setup
    req = Requisition(
        id=uuid.uuid4(),
        organization_id=staffing_org.id,
        created_by=recruiter.id,
        title="Autonomous Flight Controls Lead",
        job_description="Flight controls and embedded software.",
        status="active",
        client_organization_id=client_org.id,
    )
    db_session.add(req)
    await db_session.commit()

    sc = Scorecard(id=uuid.uuid4(), requisition_id=req.id, status="approved", version_number=1)
    db_session.add(sc)
    await db_session.commit()

    cand = Candidate(
        id=uuid.uuid4(),
        organization_id=staffing_org.id,
        full_name="Neil Armstrong",
        email="neil@nasa.gov",
        total_experience_years=12.0,
    )
    db_session.add(cand)
    await db_session.commit()

    eval_obj = Evaluation(
        id=uuid.uuid4(),
        candidate_id=cand.id,
        requisition_id=req.id,
        scorecard_id=sc.id,
        scorecard_version=1,
        total_score=96.0,
        raw_score=96.0,
        normalized_score=96.0,
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

    # 3. Client creates an interview request
    req_res = await client.post(
        f"/api/v1/client/submissions/{submission_id}/requests",
        json={
            "request_type": "INTERVIEW",
            "details": "Would like to schedule a 1-hour panel interview next Monday at 2 PM.",
        },
        headers=client_headers,
    )
    assert req_res.status_code == 200
    client_request_id = req_res.json()["id"]

    # 4. Recruiter inspects submissions list
    rec_subs_res = await client.get("/api/v1/recruiter/submissions", headers=recruiter_headers)
    assert rec_subs_res.status_code == 200
    rec_items = rec_subs_res.json()
    assert len(rec_items) == 1
    item = rec_items[0]
    assert item["candidate_name"] == "Neil Armstrong"
    assert item["candidate_email"] == "neil@nasa.gov"
    assert item["client_organization_name"] == "SkyNet Aerospace"
    assert item["pending_requests_count"] == 1

    # 5. Recruiter responds to client interview request & updates stage to INTERVIEW_SCHEDULED
    resp_res = await client.post(
        f"/api/v1/recruiter/requests/{client_request_id}/response",
        json={
            "recruiter_response": "Confirmed with candidate! Calendar invites sent for Monday 2 PM.",
            "new_stage": "INTERVIEW_SCHEDULED",
        },
        headers=recruiter_headers,
    )
    assert resp_res.status_code == 200
    assert resp_res.json()["status"] == "RESPONDED"
    assert "Confirmed with candidate" in resp_res.json()["recruiter_response"]

    # 6. Recruiter advances candidate through stages: OFFER_EXTENDED -> HIRED
    offer_res = await client.patch(
        f"/api/v1/recruiter/submissions/{submission_id}/stage",
        json={"stage": "OFFER_EXTENDED", "reason_note": "Client extended verbal and written offer."},
        headers=recruiter_headers,
    )
    assert offer_res.status_code == 200
    assert offer_res.json()["current_stage"] == "OFFER_EXTENDED"

    hired_res = await client.patch(
        f"/api/v1/recruiter/submissions/{submission_id}/stage",
        json={"stage": "HIRED", "reason_note": "Offer accepted! Start date set for next month."},
        headers=recruiter_headers,
    )
    assert hired_res.status_code == 200
    assert hired_res.json()["current_stage"] == "HIRED"

    # 7. Check Pipeline Board reflects the HIRED stage
    board_res = await client.get("/api/v1/recruiter/pipeline", headers=recruiter_headers)
    assert board_res.status_code == 200
    board_data = board_res.json()
    hired_stage = next((s for s in board_data["stages"] if s["stage"] == "HIRED"), None)
    assert hired_stage is not None
    assert hired_stage["count"] == 1
