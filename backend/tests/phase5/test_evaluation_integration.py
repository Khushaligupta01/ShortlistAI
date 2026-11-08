from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.candidate import Candidate, CandidateEmployment, CandidateSkill
from app.models.organization import Organization, OrganizationMembership
from app.models.requisition import Requisition
from app.models.resume import Resume
from app.models.scorecard import Scorecard, ScorecardCriterion
from app.models.user import User


@pytest.fixture
async def setup_eval_env(db_session: AsyncSession):
    # Staffing Org 1
    org1 = Organization(id=uuid.uuid4(), name="Tech Recruiting Corp", org_type="staffing_firm")
    # Client Org
    org2 = Organization(id=uuid.uuid4(), name="Client Enterprise", org_type="client_company")
    db_session.add_all([org1, org2])
    await db_session.flush()

    # Recruiter
    recruiter = User(
        id=uuid.uuid4(),
        email=f"recruiter_{uuid.uuid4().hex[:6]}@techrecruiting.com",
        password_hash="fakehash",
        display_name="Sarah Recruiter",
    )
    # Client User
    client_user = User(
        id=uuid.uuid4(),
        email=f"client_{uuid.uuid4().hex[:6]}@client.com",
        password_hash="fakehash",
        display_name="Hiring Manager",
    )
    db_session.add_all([recruiter, client_user])
    await db_session.flush()

    m1 = OrganizationMembership(
        id=uuid.uuid4(),
        user_id=recruiter.id,
        organization_id=org1.id,
        role="recruiter",
        is_active=True,
    )
    m2 = OrganizationMembership(
        id=uuid.uuid4(),
        user_id=client_user.id,
        organization_id=org1.id,  # Shared membership for role test
        role="client_hiring_manager",
        is_active=True,
    )
    db_session.add_all([m1, m2])
    await db_session.flush()

    # Requisition
    req = Requisition(
        id=uuid.uuid4(),
        organization_id=org1.id,
        created_by=recruiter.id,
        title="Senior Java Developer",
        job_description="Seeking a Senior Java Developer with 5-8 years experience in Java and Spring Boot in Noida.",
        status="active",
    )
    db_session.add(req)
    await db_session.flush()

    # Approved Scorecard
    sc = Scorecard(
        id=uuid.uuid4(),
        requisition_id=req.id,
        version_number=1,
        status="approved",
        experience_min=5,
        experience_max=8,
        location="Noida",
        max_notice_days=60,
        total_weight=100,
        scoring_config={
            "experience": 30,
            "must_have_skills": 40,
            "notice_period": 15,
            "location": 10,
            "nice_to_have_skills": 5,
        },
    )
    db_session.add(sc)
    await db_session.flush()

    c_exp = ScorecardCriterion(
        id=uuid.uuid4(),
        scorecard_id=sc.id,
        criterion_type="experience",
        criterion_name="5-8 Years Experience",
        label="Experience",
        weight=30,
        is_mandatory=True,
        config_json={"min_years": 5.0, "max_years": 8.0},
    )
    c_java = ScorecardCriterion(
        id=uuid.uuid4(),
        scorecard_id=sc.id,
        criterion_type="must_have_skill",
        criterion_name="Java",
        label="Java",
        weight=20,
        is_mandatory=True,
    )
    c_spring = ScorecardCriterion(
        id=uuid.uuid4(),
        scorecard_id=sc.id,
        criterion_type="must_have_skill",
        criterion_name="Spring Boot",
        label="Spring Boot",
        weight=20,
        is_mandatory=True,
    )
    c_notice = ScorecardCriterion(
        id=uuid.uuid4(),
        scorecard_id=sc.id,
        criterion_type="notice_period",
        criterion_name="Max 60 Days Notice",
        label="Notice",
        weight=15,
        is_mandatory=True,
        config_json={"max_notice_days": 60},
    )
    c_loc = ScorecardCriterion(
        id=uuid.uuid4(),
        scorecard_id=sc.id,
        criterion_type="location",
        criterion_name="Noida",
        label="Location",
        weight=10,
        is_mandatory=True,
        config_json={"location": "Noida"},
    )
    c_nth = ScorecardCriterion(
        id=uuid.uuid4(),
        scorecard_id=sc.id,
        criterion_type="nice_to_have_skill",
        criterion_name="Microservices",
        label="Microservices",
        weight=5,
        is_mandatory=False,
    )
    db_session.add_all([c_exp, c_java, c_spring, c_notice, c_loc, c_nth])
    await db_session.flush()

    # Candidate 1: Strong Candidate (Alex Mercer)
    cand_strong = Candidate(
        id=uuid.uuid4(),
        organization_id=org1.id,
        full_name="Alex Mercer",
        email="alex.mercer@example.com",
        phone="+1-555-987-6543",
        location="Noida, India",
        notice_period_days=30,
        total_experience_years=7.5,
    )
    db_session.add(cand_strong)
    await db_session.flush()

    s1 = CandidateSkill(
        id=uuid.uuid4(),
        candidate_id=cand_strong.id,
        raw_name="Java",
        name="java",
        evidence="7 years core Java experience building microservices.",
    )
    s2 = CandidateSkill(
        id=uuid.uuid4(),
        candidate_id=cand_strong.id,
        raw_name="Spring Boot",
        name="spring_boot",
        evidence="Built production REST APIs using Spring Boot 3.",
    )
    s3 = CandidateSkill(
        id=uuid.uuid4(),
        candidate_id=cand_strong.id,
        raw_name="Microservices",
        name="microservices",
        evidence="Designed distributed microservices architecture.",
    )
    db_session.add_all([s1, s2, s3])

    r1 = Resume(
        id=uuid.uuid4(),
        candidate_id=cand_strong.id,
        organization_id=org1.id,
        requisition_id=req.id,
        file_name="01_strong_java_senior.pdf",
        storage_path="test/01.pdf",
        mime_type="application/pdf",
        file_size_bytes=1000,
        parse_status="parsed",
        raw_text="Alex Mercer. 7.5 years experience as Lead Java Developer in Noida. Expert in Java, Spring Boot, Microservices. Notice period 30 days.",
    )
    db_session.add(r1)

    # Candidate 2: Partial Candidate (Missing Spring Boot and Notice)
    cand_partial = Candidate(
        id=uuid.uuid4(),
        organization_id=org1.id,
        full_name="Devin Parker",
        email="devin.parker@example.com",
        phone="+1-555-456-7890",
        location="Noida",
        notice_period_days=None,  # Missing
        total_experience_years=6.0,
    )
    db_session.add(cand_partial)
    await db_session.flush()

    ps1 = CandidateSkill(
        id=uuid.uuid4(),
        candidate_id=cand_partial.id,
        raw_name="Java",
        name="java",
        evidence="6 years of Java.",
    )
    db_session.add(ps1)

    r2 = Resume(
        id=uuid.uuid4(),
        candidate_id=cand_partial.id,
        organization_id=org1.id,
        requisition_id=req.id,
        file_name="02_partial.docx",
        storage_path="test/02.docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        file_size_bytes=1000,
        parse_status="parsed",
        raw_text="Devin Parker. 6 years Java developer in Noida. Strong background in relational databases.",
    )
    db_session.add(r2)

    await db_session.commit()

    recruiter_token = create_access_token(
        data={"sub": str(recruiter.id), "org_id": str(org1.id), "role": "recruiter"}
    )
    client_token = create_access_token(
        data={"sub": str(client_user.id), "org_id": str(org1.id), "role": "client_hiring_manager"}
    )

    return {
        "org1_id": org1.id,
        "req_id": req.id,
        "recruiter_id": recruiter.id,
        "cand_strong_id": cand_strong.id,
        "cand_partial_id": cand_partial.id,
        "recruiter_headers": {"Authorization": f"Bearer {recruiter_token}"},
        "client_headers": {"Authorization": f"Bearer {client_token}"},
    }


@pytest.mark.asyncio
async def test_single_candidate_evaluation_flow(client: AsyncClient, setup_eval_env):
    data = setup_eval_env
    req_id = data["req_id"]
    cand_id = data["cand_strong_id"]
    headers = data["recruiter_headers"]

    # 1. Trigger single candidate evaluation
    eval_resp = await client.post(
        f"/api/v1/requisitions/{req_id}/candidates/{cand_id}/evaluate",
        headers=headers,
    )
    assert eval_resp.status_code == 200
    eval_data = eval_resp.json()
    assert eval_data["candidate_name"] == "Alex Mercer"
    assert eval_data["normalized_score"] == 100.0
    assert eval_data["raw_score"] == 100.0
    assert eval_data["confidence_level"] == "HIGH"
    assert eval_data["evidence_coverage"] == 100.0

    eval_id = eval_data["id"]

    # 2. Get detailed evaluation
    get_resp = await client.get(f"/api/v1/evaluations/{eval_id}", headers=headers)
    assert get_resp.status_code == 200
    res_data = get_resp.json()
    assert res_data["total_score"] == 100.0

    # 3. Get criterion-level evidence
    ev_resp = await client.get(f"/api/v1/evaluations/{eval_id}/evidence", headers=headers)
    assert ev_resp.status_code == 200
    evidence_list = ev_resp.json()
    assert len(evidence_list) >= 5
    java_ev = next(e for e in evidence_list if e["criterion_name"] == "Java")
    assert java_ev["evidence_status"] == "MATCHED"
    assert java_ev["awarded_points"] == 20.0

    # 4. Save recruiter review
    review_resp = await client.post(
        f"/api/v1/evaluations/{eval_id}/review",
        json={"decision": "SHORTLIST", "notes": "Strong candidate matching all criteria."},
        headers=headers,
    )
    assert review_resp.status_code == 200
    rev_data = review_resp.json()
    assert rev_data["decision"] == "SHORTLIST"

    # 5. Recalculate evaluation
    recalc_resp = await client.post(
        f"/api/v1/evaluations/{eval_id}/recalculate",
        headers=headers,
    )
    assert recalc_resp.status_code == 200
    recalc_data = recalc_resp.json()
    assert recalc_data["normalized_score"] == 100.0


@pytest.mark.asyncio
async def test_batch_evaluation_flow(client: AsyncClient, setup_eval_env):
    from tests.conftest import TestSessionLocal
    from app.services.evaluation_service import evaluation_service

    # Configure test session factory for background execution
    orig_sf = evaluation_service.session_factory
    evaluation_service.session_factory = TestSessionLocal

    try:
        data = setup_eval_env
        req_id = data["req_id"]
        headers = data["recruiter_headers"]

        # 1. Start batch evaluation
        batch_resp = await client.post(
            f"/api/v1/requisitions/{req_id}/evaluations",
            json={},
            headers=headers,
        )
        assert batch_resp.status_code == 202
        run_data = batch_resp.json()
        run_id = run_data["id"]
        assert run_data["total_candidates"] >= 2

        # 2. Process batch jobs synchronously for deterministic testing
        await evaluation_service.process_batch_jobs(
            run_id=uuid.UUID(run_id),
            requisition_id=req_id,
            organization_id=data["org1_id"],
            user_id=data["recruiter_id"],
            candidate_ids=[data["cand_strong_id"], data["cand_partial_id"]],
        )

        # 3. Poll evaluation run
        run_resp = await client.get(
            f"/api/v1/requisitions/{req_id}/evaluation-runs/{run_id}",
            headers=headers,
        )
        assert run_resp.status_code == 200
        run_status = run_resp.json()
        assert run_status["id"] == run_id
        assert run_status["status"] == "COMPLETED"

        # 4. List evaluations for requisition
        list_resp = await client.get(
            f"/api/v1/requisitions/{req_id}/evaluations?sort_by=score_desc",
            headers=headers,
        )
        assert list_resp.status_code == 200
        list_data = list_resp.json()
        assert "items" in list_data
        assert list_data["total"] >= 2
    finally:
        evaluation_service.session_factory = orig_sf


@pytest.mark.asyncio
async def test_client_pii_masking_and_rbac(client: AsyncClient, setup_eval_env):
    data = setup_eval_env
    req_id = data["req_id"]
    cand_id = data["cand_strong_id"]

    # 1. Recruiter evaluates candidate
    eval_resp = await client.post(
        f"/api/v1/requisitions/{req_id}/candidates/{cand_id}/evaluate",
        headers=data["recruiter_headers"],
    )
    assert eval_resp.status_code == 200
    eval_id = eval_resp.json()["id"]

    # 2. Client views evaluation: email must be masked
    client_eval_resp = await client.get(
        f"/api/v1/evaluations/{eval_id}",
        headers=data["client_headers"],
    )
    assert client_eval_resp.status_code == 200
    client_data = client_eval_resp.json()
    assert "***@" in client_data["candidate_email"]

    # 3. Client user cannot trigger recruiter review (403)
    client_rev_resp = await client.post(
        f"/api/v1/evaluations/{eval_id}/review",
        json={"decision": "SHORTLIST"},
        headers=data["client_headers"],
    )
    assert client_rev_resp.status_code == 403
