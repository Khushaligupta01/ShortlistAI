from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate, CandidateEducation, CandidateEmployment, CandidateSkill
from app.models.evaluation import Evaluation, RecruiterReview
from app.models.requisition import Requisition
from app.models.resume import Resume
from app.models.scorecard import Scorecard
from tests.conftest import auth_headers, seed_user_with_org


@pytest.mark.asyncio
async def test_candidate_profile_and_history(client: AsyncClient, db_session: AsyncSession):
    recruiter, org = await seed_user_with_org(
        db_session, email="profile_recruiter@example.com", password="Password123!", role="recruiter"
    )
    headers = auth_headers(recruiter.id, "recruiter", org.id)

    # Requisition & Scorecards
    req = Requisition(
        id=uuid.uuid4(),
        organization_id=org.id,
        created_by=recruiter.id,
        title="Senior Cloud Architect",
        job_description="AWS, Kubernetes, Terraform",
        status="active",
        location="Remote",
    )
    db_session.add(req)
    await db_session.commit()

    sc_v1 = Scorecard(id=uuid.uuid4(), requisition_id=req.id, status="superseded", version_number=1)
    sc_v2 = Scorecard(id=uuid.uuid4(), requisition_id=req.id, status="approved", version_number=2)
    db_session.add_all([sc_v1, sc_v2])
    await db_session.commit()

    # Candidate with complete profile
    cand = Candidate(
        id=uuid.uuid4(),
        organization_id=org.id,
        full_name="Morgan Freeman",
        email="morgan@cloudexperts.com",
        phone="+1 555 123 4567",
        location="San Francisco, CA",
        notice_period_days=30,
        total_experience_years=10.5,
    )
    db_session.add(cand)
    await db_session.commit()

    # Employments & Educations & Skills & Resumes
    emp = CandidateEmployment(
        id=uuid.uuid4(),
        candidate_id=cand.id,
        company="Databricks",
        job_title="Lead Infrastructure Engineer",
        start_date="2020-01",
        end_date="2024-05",
        is_current=True,
        description="Managed 1,000+ k8s nodes on AWS",
        technologies=["AWS", "Kubernetes", "Terraform"],
    )
    edu = CandidateEducation(
        id=uuid.uuid4(),
        candidate_id=cand.id,
        institution="UC Berkeley",
        qualification="B.S.",
        field_of_study="Computer Science",
        graduation_year=2014,
    )
    sk1 = CandidateSkill(id=uuid.uuid4(), candidate_id=cand.id, name="aws", raw_name="Amazon Web Services")
    sk2 = CandidateSkill(id=uuid.uuid4(), candidate_id=cand.id, name="kubernetes", raw_name="Kubernetes")
    res_file = Resume(
        id=uuid.uuid4(),
        candidate_id=cand.id,
        organization_id=org.id,
        requisition_id=req.id,
        file_name="morgan_resume.pdf",
        storage_path="/storage/morgan_resume.pdf",
        mime_type="application/pdf",
        file_size_bytes=45000,
        parse_status="parsed",
    )
    db_session.add_all([emp, edu, sk1, sk2, res_file])
    await db_session.commit()

    # Evaluations: History across Scorecard v1 and v2
    ev1 = Evaluation(
        id=uuid.uuid4(),
        candidate_id=cand.id,
        requisition_id=req.id,
        scorecard_id=sc_v1.id,
        organization_id=org.id,
        version_number=1,
        scorecard_version=1,
        total_score=78.0,
        raw_score=78.0,
        normalized_score=78.0,
        evidence_coverage=0.8,
        confidence_level="HIGH",
        evaluation_status="COMPLETED",
        is_current=False,
        score_breakdown_json={"summary": "Initial screening on scorecard v1"},
    )
    ev2 = Evaluation(
        id=uuid.uuid4(),
        candidate_id=cand.id,
        requisition_id=req.id,
        scorecard_id=sc_v2.id,
        organization_id=org.id,
        version_number=2,
        scorecard_version=2,
        total_score=92.0,
        raw_score=92.0,
        normalized_score=92.0,
        evidence_coverage=0.95,
        confidence_level="HIGH",
        evaluation_status="COMPLETED",
        is_current=True,
        score_breakdown_json={"summary": "Re-evaluated against approved scorecard v2 with strong architecture evidence"},
    )
    db_session.add_all([ev1, ev2])
    await db_session.commit()

    # Recruiter review on ev2
    review = RecruiterReview(
        id=uuid.uuid4(),
        evaluation_id=ev2.id,
        recruiter_id=recruiter.id,
        organization_id=org.id,
        decision="SHORTLIST",
        notes="Top tier infrastructure talent",
    )
    db_session.add(review)
    await db_session.commit()

    # --- Test 1: Full Candidate Profile Detail ---
    detail_res = await client.get(f"/api/v1/candidates/{cand.id}", headers=headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["full_name"] == "Morgan Freeman"
    assert detail["email"] == "morgan@cloudexperts.com"
    assert len(detail["employments"]) == 1
    assert detail["employments"][0]["company"] == "Databricks"
    assert len(detail["educations"]) == 1
    assert detail["educations"][0]["institution"] == "UC Berkeley"
    assert len(detail["skills"]) == 2
    assert len(detail["resumes"]) == 1
    assert detail["resumes"][0]["file_name"] == "morgan_resume.pdf"

    # --- Test 2: Candidate Evaluation History ---
    hist_res = await client.get(f"/api/v1/candidates/{cand.id}/evaluations", headers=headers)
    assert hist_res.status_code == 200
    history = hist_res.json()
    assert len(history) == 2
    # Newest version (v2) should be first
    assert history[0]["scorecard_version"] == 2
    assert history[0]["overall_score"] == 92.0
    assert history[0]["is_current"] is True
    assert history[0]["review_decision"] == "SHORTLIST"
    assert history[1]["scorecard_version"] == 1
    assert history[1]["is_current"] is False

    # --- Test 3: Requisition Summary ---
    sum_res = await client.get(f"/api/v1/requisitions/{req.id}/summary", headers=headers)
    assert sum_res.status_code == 200
    summary = sum_res.json()
    assert summary["candidate_count"] == 1
    assert summary["evaluated_count"] == 1
    assert summary["shortlisted_count"] == 1
    assert summary["average_score"] == 92.0
    assert summary["top_score"] == 92.0
    assert summary["scorecard_version"] == 2

    # --- Test 4: Requisition Candidates ---
    req_cand_res = await client.get(f"/api/v1/requisitions/{req.id}/candidates", headers=headers)
    assert req_cand_res.status_code == 200
    req_cands = req_cand_res.json()
    assert req_cands["total"] == 1
    assert req_cands["items"][0]["full_name"] == "Morgan Freeman"
    assert req_cands["items"][0]["evaluation_score"] == 92.0
    assert req_cands["items"][0]["review_decision"] == "SHORTLIST"
