from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate, CandidateEmployment, CandidateSkill
from app.models.evaluation import Evaluation, EvaluationEvidence
from app.models.requisition import Requisition
from app.models.scorecard import Scorecard, ScorecardCriterion
from tests.conftest import auth_headers, create_test_org, seed_user_with_org


@pytest.mark.asyncio
async def test_phase7_end_to_end_client_portal_and_pipeline_lifecycle(client: AsyncClient, db_session: AsyncSession):
    # 1. Setup staffing firm & client company
    recruiter, staffing_org = await seed_user_with_org(
        db_session, email="rec_e2e7@staffing.com", password="Password123!", role="recruiter", org_name="Horizon Tech Partners"
    )
    recruiter_headers = auth_headers(recruiter.id, "recruiter", staffing_org.id)

    client_org = await create_test_org(db_session, name="FinGlobal Banking", org_type="client_company")
    client_user, _ = await seed_user_with_org(
        db_session, email="hm_e2e7@finglobal.com", password="Password123!", role="client_hiring_manager", org_name="FinGlobal Banking"
    )
    client_headers = auth_headers(client_user.id, "client_hiring_manager", client_org.id)

    # 2. Requisition creation & scorecard approval
    req = Requisition(
        id=uuid.uuid4(),
        organization_id=staffing_org.id,
        created_by=recruiter.id,
        title="VP of Engineering - Cloud & Payments",
        job_description="Lead modern payments platform with cloud-native resilience.",
        status="active",
        client_organization_id=client_org.id,
    )
    db_session.add(req)
    await db_session.commit()

    sc = Scorecard(id=uuid.uuid4(), requisition_id=req.id, status="approved", version_number=1)
    db_session.add(sc)
    await db_session.commit()

    crit = ScorecardCriterion(
        id=uuid.uuid4(),
        scorecard_id=sc.id,
        criterion_type="must_have",
        criterion_name="High-throughput Payments",
        label="Payments Architecture",
        weight=50,
    )
    db_session.add(crit)
    await db_session.commit()

    # 3. Candidate creation & evaluation
    cand = Candidate(
        id=uuid.uuid4(),
        organization_id=staffing_org.id,
        full_name="Katherine Johnson",
        email="katherine@nasa.gov",
        phone="+1 757-555-0100",
        location="Hampton, VA 23666",
        total_experience_years=16.0,
        notice_period_days=15,
    )
    emp = CandidateEmployment(
        id=uuid.uuid4(),
        candidate_id=cand.id,
        job_title="Director of Platform Reliability",
        company="Stripe Global",
        start_date="2019-01-01",
        is_current=True,
        description="Scaled payment processing gateway handling 100k TPS.",
    )
    skill = CandidateSkill(id=uuid.uuid4(), candidate_id=cand.id, name="Distributed Systems", raw_name="Distributed Systems")
    db_session.add_all([cand, emp, skill])
    await db_session.commit()

    eval_obj = Evaluation(
        id=uuid.uuid4(),
        candidate_id=cand.id,
        requisition_id=req.id,
        scorecard_id=sc.id,
        scorecard_version=1,
        total_score=97.0,
        raw_score=97.0,
        normalized_score=97.0,
        evaluation_status="completed",
    )
    db_session.add(eval_obj)
    await db_session.commit()

    ev_item = EvaluationEvidence(
        id=uuid.uuid4(),
        evaluation_id=eval_obj.id,
        scorecard_criterion_id=crit.id,
        evidence_status="MATCH",
        confidence_score=1.0,
        evidence_text="Scaled payment processing gateway handling 100k TPS.",
        explanation="Direct verified match for high-throughput architecture.",
    )
    db_session.add(ev_item)
    await db_session.commit()

    # 4. Recruiter submits candidate to client
    sub_res = await client.post(
        f"/api/v1/requisitions/{req.id}/submissions",
        json={
            "candidate_id": str(cand.id),
            "client_organization_id": str(client_org.id),
            "recruiter_notes_for_client": "Top candidate in our network. Strong culture fit and immediate impact.",
        },
        headers=recruiter_headers,
    )
    assert sub_res.status_code == 201
    sub_data = sub_res.json()
    submission_id = sub_data["submission_id"]
    candidate_ref = sub_data["candidate_reference"]

    # 5. Client views masked candidate profile
    client_profile_res = await client.get(
        f"/api/v1/client/submissions/{submission_id}",
        headers=client_headers,
    )
    assert client_profile_res.status_code == 200
    profile = client_profile_res.json()

    # Zero PII check
    assert profile["candidate_reference"] == candidate_ref
    assert "katherine" not in str(profile).lower()
    assert "johnson" not in str(profile).lower()
    assert "757-555" not in str(profile)
    assert "23666" not in profile["location"]

    # Experience & evidence present
    assert profile["overall_score"] == 97.0
    assert profile["criterion_evaluations"][0]["criterion_name"] == "High-throughput Payments"
    assert profile["employments"][0]["title"] == "Director of Platform Reliability"
    assert profile["recruiter_notes_for_client"] == "Top candidate in our network. Strong culture fit and immediate impact."

    # 6. Client requests an interview with detailed notes
    intv_res = await client.post(
        f"/api/v1/client/submissions/{submission_id}/decisions",
        json={
            "decision": "INTERVIEW_REQUESTED",
            "reason_note": "Unanimous approval to proceed to VP panel.",
            "interview_details": "60-min interview with CTO and Head of Banking next Thursday at 3 PM EST.",
        },
        headers=client_headers,
    )
    assert intv_res.status_code == 200
    assert intv_res.json()["current_stage"] == "INTERVIEW_REQUESTED"

    # 7. Recruiter checks requests and responds
    rec_subs_res = await client.get(
        "/api/v1/recruiter/submissions",
        headers=recruiter_headers,
    )
    assert rec_subs_res.status_code == 200
    assert rec_subs_res.json()[0]["pending_requests_count"] == 1

    # Fetch request ID from client profile
    refreshed_prof = (await client.get(f"/api/v1/client/submissions/{submission_id}", headers=client_headers)).json()
    assert len(refreshed_prof["requests"]) == 1
    req_item = refreshed_prof["requests"][0]
    request_id = req_item["id"]

    # Recruiter confirms interview schedule
    resp_res = await client.post(
        f"/api/v1/recruiter/requests/{request_id}/response",
        json={
            "recruiter_response": "Confirmed with Katherine for Thursday 3 PM EST. Google Meet invites sent.",
            "new_stage": "INTERVIEW_SCHEDULED",
        },
        headers=recruiter_headers,
    )
    assert resp_res.status_code == 200
    assert resp_res.json()["status"] == "RESPONDED"

    # 8. Post-interview: Client shortlists & makes offer
    client_short_res = await client.post(
        f"/api/v1/client/submissions/{submission_id}/decisions",
        json={
            "decision": "CLIENT_SHORTLISTED",
            "reason_note": "Panel interview went amazingly well. Moving to offer stage.",
        },
        headers=client_headers,
    )
    assert client_short_res.status_code == 200
    assert client_short_res.json()["current_stage"] == "CLIENT_SHORTLISTED"

    # Recruiter marks hired
    hired_res = await client.patch(
        f"/api/v1/recruiter/submissions/{submission_id}/stage",
        json={"stage": "HIRED", "reason_note": "Offer signed and accepted!"},
        headers=recruiter_headers,
    )
    assert hired_res.status_code == 200
    assert hired_res.json()["current_stage"] == "HIRED"

    # 9. Verify full audit trail and pipeline records
    history_res = await client.get(
        f"/api/v1/client/submissions/{submission_id}/history",
        headers=client_headers,
    )
    assert history_res.status_code == 200
    history = history_res.json()
    stages = [h["current_stage"] for h in history]
    assert stages == ["HIRED", "CLIENT_SHORTLISTED", "INTERVIEW_SCHEDULED", "INTERVIEW_REQUESTED", "SUBMITTED"]
