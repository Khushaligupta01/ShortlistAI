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
from app.models.submission import PipelineRecord, Submission
from tests.conftest import auth_headers, create_test_org, seed_user_with_org


@pytest.mark.asyncio
async def test_candidate_submission_workflow_and_validation(client: AsyncClient, db_session: AsyncSession):
    # 1. Setup staffing firm & client
    recruiter, staffing_org = await seed_user_with_org(
        db_session, email="rec_sub@staffing.com", password="Password123!", role="recruiter", org_name="Staffing Sub Test"
    )
    headers = auth_headers(recruiter.id, "recruiter", staffing_org.id)

    client_org = await create_test_org(db_session, name="Enterprise Client Corp", org_type="client_company")

    # 2. Create Requisition
    req = Requisition(
        id=uuid.uuid4(),
        organization_id=staffing_org.id,
        created_by=recruiter.id,
        title="Full Stack Tech Lead",
        job_description="Lead engineer with React and Python experience.",
        status="active",
    )
    db_session.add(req)
    await db_session.commit()

    # 3. Create Candidate without evaluation
    cand = Candidate(
        id=uuid.uuid4(),
        organization_id=staffing_org.id,
        full_name="Grace Hopper",
        email="grace@navy.mil",
        location="Arlington, VA",
        total_experience_years=15.0,
    )
    db_session.add(cand)
    await db_session.commit()

    # 4. Attempt submission without evaluation -> expect 400 Bad Request
    sub_payload = {
        "candidate_id": str(cand.id),
        "client_organization_id": str(client_org.id),
        "recruiter_notes_for_client": "Strong visionary leader.",
    }
    fail_res = await client.post(
        f"/api/v1/requisitions/{req.id}/submissions",
        json=sub_payload,
        headers=headers,
    )
    assert fail_res.status_code == 400
    fail_json = fail_res.json()
    err_text = str(fail_json.get("detail") or fail_json.get("message") or fail_json).lower()
    assert "evaluated" in err_text

    # 5. Create Scorecard and Evaluation
    sc = Scorecard(
        id=uuid.uuid4(),
        requisition_id=req.id,
        status="approved",
        version_number=1,
    )
    db_session.add(sc)
    await db_session.commit()

    eval_obj = Evaluation(
        id=uuid.uuid4(),
        candidate_id=cand.id,
        requisition_id=req.id,
        scorecard_id=sc.id,
        scorecard_version=1,
        total_score=88.0,
        raw_score=88.0,
        normalized_score=88.0,
        evaluation_status="completed",
    )
    db_session.add(eval_obj)
    await db_session.commit()

    # 6. Now submit evaluated candidate -> expect 201 Created
    success_res = await client.post(
        f"/api/v1/requisitions/{req.id}/submissions",
        json=sub_payload,
        headers=headers,
    )
    assert success_res.status_code == 201
    res_data = success_res.json()
    assert res_data["current_stage"] == "SUBMITTED"
    assert res_data["candidate_reference"].startswith("Candidate CND-")
    submission_id = uuid.UUID(res_data["submission_id"])

    # 7. Verify DB persistence and initial PipelineRecord
    sub_query = await db_session.execute(
        select(Submission).where(Submission.id == submission_id)
    )
    saved_sub = sub_query.scalar_one()
    assert saved_sub.candidate_id == cand.id
    assert saved_sub.client_organization_id == client_org.id
    assert saved_sub.current_stage == "SUBMITTED"
    assert saved_sub.recruiter_notes_for_client == "Strong visionary leader."

    p_query = await db_session.execute(
        select(PipelineRecord).where(PipelineRecord.submission_id == submission_id)
    )
    pipeline_recs = p_query.scalars().all()
    assert len(pipeline_recs) == 1
    assert pipeline_recs[0].current_stage == "SUBMITTED"
    assert pipeline_recs[0].previous_stage is None
    assert pipeline_recs[0].changed_by == recruiter.id

    # 8. Duplicate active submission attempt -> expect 409 Conflict
    dup_res = await client.post(
        f"/api/v1/requisitions/{req.id}/submissions",
        json=sub_payload,
        headers=headers,
    )
    assert dup_res.status_code == 409
    dup_json = dup_res.json()
    dup_text = str(dup_json.get("detail") or dup_json.get("message") or dup_json).lower()
    assert "already been submitted" in dup_text
