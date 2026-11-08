from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.evaluation import Evaluation, RecruiterReview
from app.models.requisition import Requisition
from app.models.resume import Resume
from app.models.scorecard import Scorecard
from tests.conftest import auth_headers, seed_user_with_org


@pytest.mark.asyncio
async def test_dashboard_metrics_aggregation(client: AsyncClient, db_session: AsyncSession):
    recruiter, org = await seed_user_with_org(
        db_session, email="metrics_recruiter@example.com", password="Password123!", role="recruiter"
    )
    headers = auth_headers(recruiter.id, "recruiter", org.id)

    # 1. Requisitions: 1 active, 1 draft
    req1 = Requisition(
        id=uuid.uuid4(),
        organization_id=org.id,
        created_by=recruiter.id,
        title="Active Backend Role",
        job_description="Python FastApi Engineer",
        status="active",
    )
    req2 = Requisition(
        id=uuid.uuid4(),
        organization_id=org.id,
        created_by=recruiter.id,
        title="Draft Frontend Role",
        job_description="React Next.js Engineer",
        status="draft",
    )
    db_session.add_all([req1, req2])
    await db_session.commit()

    # 2. Scorecard
    sc = Scorecard(
        id=uuid.uuid4(),
        requisition_id=req1.id,
        status="approved",
        version_number=1,
    )
    db_session.add(sc)
    await db_session.commit()

    # 3. Candidates: 3 candidates
    c1 = Candidate(id=uuid.uuid4(), organization_id=org.id, full_name="Candidate One", email="c1@example.com")
    c2 = Candidate(id=uuid.uuid4(), organization_id=org.id, full_name="Candidate Two", email="c2@example.com")
    c3 = Candidate(id=uuid.uuid4(), organization_id=org.id, full_name="Candidate Three", email="c3@example.com")
    db_session.add_all([c1, c2, c3])
    await db_session.commit()

    # 4. Resumes: 1 parsed, 1 pending, 1 failed
    r1 = Resume(
        id=uuid.uuid4(),
        candidate_id=c1.id,
        organization_id=org.id,
        requisition_id=req1.id,
        file_name="c1.pdf",
        storage_path="/storage/c1.pdf",
        mime_type="application/pdf",
        file_size_bytes=1000,
        parse_status="parsed",
    )
    r2 = Resume(
        id=uuid.uuid4(),
        candidate_id=c2.id,
        organization_id=org.id,
        requisition_id=req1.id,
        file_name="c2.pdf",
        storage_path="/storage/c2.pdf",
        mime_type="application/pdf",
        file_size_bytes=2000,
        parse_status="pending",
    )
    r3 = Resume(
        id=uuid.uuid4(),
        candidate_id=c3.id,
        organization_id=org.id,
        requisition_id=req1.id,
        file_name="c3.pdf",
        storage_path="/storage/c3.pdf",
        mime_type="application/pdf",
        file_size_bytes=3000,
        parse_status="failed",
    )
    db_session.add_all([r1, r2, r3])
    await db_session.commit()

    # 5. Evaluations: 2 completed
    ev1 = Evaluation(
        id=uuid.uuid4(),
        candidate_id=c1.id,
        requisition_id=req1.id,
        scorecard_id=sc.id,
        organization_id=org.id,
        total_score=85.0,
        raw_score=85.0,
        normalized_score=85.0,
        evidence_coverage=0.9,
        confidence_level="HIGH",
        evaluation_status="COMPLETED",
        is_current=True,
        score_breakdown_json={"experience": {"awarded": 20, "max": 20}},
    )
    ev2 = Evaluation(
        id=uuid.uuid4(),
        candidate_id=c2.id,
        requisition_id=req1.id,
        scorecard_id=sc.id,
        organization_id=org.id,
        total_score=65.0,
        raw_score=65.0,
        normalized_score=65.0,
        evidence_coverage=0.7,
        confidence_level="NEEDS_REVIEW",
        evaluation_status="COMPLETED",
        is_current=True,
        score_breakdown_json={"experience": {"awarded": 15, "max": 20}},
    )
    db_session.add_all([ev1, ev2])
    await db_session.commit()

    # 6. Recruiter Review: 1 SHORTLIST for ev1, none for ev2
    review1 = RecruiterReview(
        id=uuid.uuid4(),
        evaluation_id=ev1.id,
        recruiter_id=recruiter.id,
        organization_id=org.id,
        decision="SHORTLIST",
        notes="Strong candidate for backend",
    )
    db_session.add(review1)
    await db_session.commit()

    # Request metrics endpoint
    resp = await client.get("/api/v1/recruiter/metrics", headers=headers)
    assert resp.status_code == 200
    metrics = resp.json()

    assert metrics["active_requisitions"] == 1
    assert metrics["total_candidates"] == 3
    assert metrics["resumes_processed"] == 1
    assert metrics["resumes_pending"] == 1
    assert metrics["failed_jobs"] == 1
    assert metrics["completed_evaluations"] == 2
    assert metrics["candidates_awaiting_review"] == 1
    assert metrics["candidates_shortlisted"] == 1


@pytest.mark.asyncio
async def test_dashboard_full_and_isolation(client: AsyncClient, db_session: AsyncSession):
    r1, org1 = await seed_user_with_org(db_session, "r1@org1.com", "Password123!", "recruiter", "Org 1")
    r2, org2 = await seed_user_with_org(db_session, "r2@org2.com", "Password123!", "recruiter", "Org 2")

    # Seed 1 active req in Org 1
    req = Requisition(
        id=uuid.uuid4(),
        organization_id=org1.id,
        created_by=r1.id,
        title="Org 1 Role",
        job_description="Role description",
        status="active",
    )
    db_session.add(req)
    await db_session.commit()

    # Org 1 dashboard
    resp1 = await client.get("/api/v1/recruiter/dashboard", headers=auth_headers(r1.id, "recruiter", org1.id))
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["metrics"]["active_requisitions"] == 1
    assert len(data1["requisitions"]) == 1
    assert data1["requisitions"][0]["title"] == "Org 1 Role"

    # Org 2 dashboard (must be empty/isolated)
    resp2 = await client.get("/api/v1/recruiter/dashboard", headers=auth_headers(r2.id, "recruiter", org2.id))
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["metrics"]["active_requisitions"] == 0
    assert len(data2["requisitions"]) == 0
    assert data2["metrics"]["total_candidates"] == 0


@pytest.mark.asyncio
async def test_dashboard_activity_feed(client: AsyncClient, db_session: AsyncSession):
    recruiter, org = await seed_user_with_org(db_session, "activity_rec@example.com", "Password123!", "recruiter")
    headers = auth_headers(recruiter.id, "recruiter", org.id)

    # Create Requisition
    req = Requisition(
        id=uuid.uuid4(),
        organization_id=org.id,
        created_by=recruiter.id,
        title="Principal AI Architect",
        job_description="AI Architecture and LLMs",
        status="active",
    )
    db_session.add(req)
    await db_session.commit()

    resp = await client.get("/api/v1/recruiter/activity?limit=5", headers=headers)
    assert resp.status_code == 200
    activities = resp.json()["activities"]
    assert len(activities) >= 1
    assert any(a["type"] == "requisition_created" and "Principal AI Architect" in a["description"] for a in activities)
