from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate, CandidateEmployment, CandidateSkill
from app.models.evaluation import Evaluation, RecruiterReview
from app.models.requisition import Requisition
from app.models.resume import Resume
from app.models.scorecard import Scorecard
from tests.conftest import auth_headers, seed_user_with_org


@pytest.mark.asyncio
async def test_candidate_search_and_filtering(client: AsyncClient, db_session: AsyncSession):
    recruiter, org = await seed_user_with_org(
        db_session, email="search_filter_recruiter@example.com", password="Password123!", role="recruiter"
    )
    headers = auth_headers(recruiter.id, "recruiter", org.id)

    # 1. Requisitions
    req_backend = Requisition(
        id=uuid.uuid4(),
        organization_id=org.id,
        created_by=recruiter.id,
        title="Lead Python Engineer",
        job_description="Python distributed systems",
        status="active",
    )
    req_frontend = Requisition(
        id=uuid.uuid4(),
        organization_id=org.id,
        created_by=recruiter.id,
        title="Staff Frontend Developer",
        job_description="React, TypeScript, CSS",
        status="active",
    )
    db_session.add_all([req_backend, req_frontend])
    await db_session.commit()

    sc_b = Scorecard(id=uuid.uuid4(), requisition_id=req_backend.id, status="approved", version_number=1)
    db_session.add(sc_b)
    await db_session.commit()

    # 2. Seed 4 Candidates with varying skills, employment, location, experience, and notice days
    # Candidate A: Python, Backend, London, 8 yrs, 30 days notice
    cand_a = Candidate(
        id=uuid.uuid4(),
        organization_id=org.id,
        full_name="Alice Smith",
        email="alice@techcorp.io",
        location="London, UK",
        total_experience_years=8.0,
        notice_period_days=30,
    )
    # Candidate B: React, Frontend, Berlin, 4 yrs, 60 days notice
    cand_b = Candidate(
        id=uuid.uuid4(),
        organization_id=org.id,
        full_name="Bob Jones",
        email="bob@webinnovations.de",
        location="Berlin, Germany",
        total_experience_years=4.0,
        notice_period_days=60,
    )
    # Candidate C: Fullstack Python & React, London, 12 yrs, 15 days notice
    cand_c = Candidate(
        id=uuid.uuid4(),
        organization_id=org.id,
        full_name="Charlie Brown",
        email="charlie@bigsystems.com",
        location="London, UK",
        total_experience_years=12.0,
        notice_period_days=15,
    )
    # Candidate D: Java, NYC, 2 yrs, 90 days notice
    cand_d = Candidate(
        id=uuid.uuid4(),
        organization_id=org.id,
        full_name="Diana Prince",
        email="diana@amazon.com",
        location="New York, USA",
        total_experience_years=2.0,
        notice_period_days=90,
    )
    db_session.add_all([cand_a, cand_b, cand_c, cand_d])
    await db_session.commit()

    # Skills
    db_session.add_all([
        CandidateSkill(id=uuid.uuid4(), candidate_id=cand_a.id, name="python", raw_name="Python 3.10"),
        CandidateSkill(id=uuid.uuid4(), candidate_id=cand_a.id, name="fastapi", raw_name="FastAPI"),
        CandidateSkill(id=uuid.uuid4(), candidate_id=cand_b.id, name="react", raw_name="React.js"),
        CandidateSkill(id=uuid.uuid4(), candidate_id=cand_c.id, name="python", raw_name="Python"),
        CandidateSkill(id=uuid.uuid4(), candidate_id=cand_c.id, name="react", raw_name="React"),
        CandidateSkill(id=uuid.uuid4(), candidate_id=cand_d.id, name="java", raw_name="Java"),
    ])

    # Employments (job title and past companies for search testing)
    db_session.add_all([
        CandidateEmployment(id=uuid.uuid4(), candidate_id=cand_a.id, company="Stripe", job_title="Senior Python Backend Developer", is_current=True),
        CandidateEmployment(id=uuid.uuid4(), candidate_id=cand_b.id, company="Zalando", job_title="UI Frontend Engineer", is_current=True),
        CandidateEmployment(id=uuid.uuid4(), candidate_id=cand_c.id, company="Google", job_title="Principal Architect", is_current=True),
        CandidateEmployment(id=uuid.uuid4(), candidate_id=cand_d.id, company="Amazon", job_title="Junior Software Engineer", is_current=True),
    ])

    # Resumes linking candidates to requisitions
    r_a = Resume(id=uuid.uuid4(), candidate_id=cand_a.id, organization_id=org.id, requisition_id=req_backend.id, file_name="a.pdf", storage_path="/p/a.pdf", mime_type="application/pdf", file_size_bytes=100, parse_status="parsed")
    r_b = Resume(id=uuid.uuid4(), candidate_id=cand_b.id, organization_id=org.id, requisition_id=req_frontend.id, file_name="b.pdf", storage_path="/p/b.pdf", mime_type="application/pdf", file_size_bytes=100, parse_status="parsed")
    r_c = Resume(id=uuid.uuid4(), candidate_id=cand_c.id, organization_id=org.id, requisition_id=req_backend.id, file_name="c.pdf", storage_path="/p/c.pdf", mime_type="application/pdf", file_size_bytes=100, parse_status="parsed")
    db_session.add_all([r_a, r_b, r_c])

    # Evaluations: Charlie (95.0), Alice (80.0)
    ev_c = Evaluation(id=uuid.uuid4(), candidate_id=cand_c.id, requisition_id=req_backend.id, scorecard_id=sc_b.id, organization_id=org.id, total_score=95.0, raw_score=95.0, normalized_score=95.0, evidence_coverage=0.95, evaluation_status="COMPLETED", is_current=True)
    ev_a = Evaluation(id=uuid.uuid4(), candidate_id=cand_a.id, requisition_id=req_backend.id, scorecard_id=sc_b.id, organization_id=org.id, total_score=80.0, raw_score=80.0, normalized_score=80.0, evidence_coverage=0.85, evaluation_status="COMPLETED", is_current=True)
    db_session.add_all([ev_c, ev_a])

    # Review: Charlie shortlisted
    rev_c = RecruiterReview(id=uuid.uuid4(), evaluation_id=ev_c.id, recruiter_id=recruiter.id, organization_id=org.id, decision="SHORTLIST", notes="Outstanding architect")
    db_session.add(rev_c)
    await db_session.commit()

    # --- Test 1: Global listing and pagination ---
    res = await client.get("/api/v1/candidates?page=1&page_size=2", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 4
    assert len(data["items"]) == 2
    assert data["total_pages"] == 2

    # --- Test 2: Search by company ("Stripe") ---
    res = await client.get("/api/v1/candidates?search=Stripe", headers=headers)
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["full_name"] == "Alice Smith"
    assert items[0]["primary_company"] == "Stripe"

    # --- Test 3: Search by skill ("react") ---
    res = await client.get("/api/v1/candidates?skill=react", headers=headers)
    assert res.status_code == 200
    names = {i["full_name"] for i in res.json()["items"]}
    assert "Bob Jones" in names
    assert "Charlie Brown" in names
    assert "Alice Smith" not in names

    # --- Test 4: Filter by requisition (req_backend) ---
    res = await client.get(f"/api/v1/candidates?requisition_id={req_backend.id}", headers=headers)
    assert res.status_code == 200
    names = {i["full_name"] for i in res.json()["items"]}
    assert "Alice Smith" in names
    assert "Charlie Brown" in names
    assert "Bob Jones" not in names

    # --- Test 5: Filter by Experience range (5 to 10 yrs) ---
    res = await client.get("/api/v1/candidates?min_experience=5&max_experience=10", headers=headers)
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["full_name"] == "Alice Smith"

    # --- Test 6: Filter by Max Notice Days (<= 30 days) ---
    res = await client.get("/api/v1/candidates?max_notice_days=30", headers=headers)
    assert res.status_code == 200
    names = {i["full_name"] for i in res.json()["items"]}
    assert "Alice Smith" in names  # 30
    assert "Charlie Brown" in names  # 15
    assert "Bob Jones" not in names  # 60

    # --- Test 7: Filter by Score (>= 90) ---
    res = await client.get("/api/v1/candidates?min_score=90", headers=headers)
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["full_name"] == "Charlie Brown"
    assert items[0]["evaluation_score"] == 95.0

    # --- Test 8: Filter by Review Decision ("SHORTLIST") ---
    res = await client.get("/api/v1/candidates?review_decision=SHORTLIST", headers=headers)
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["full_name"] == "Charlie Brown"
    assert items[0]["review_decision"] == "SHORTLIST"

    # --- Test 9: Deterministic Sorting by Score descending ---
    res = await client.get("/api/v1/candidates?sort_by=score&sort_order=desc", headers=headers)
    assert res.status_code == 200
    items = res.json()["items"]
    # Charlie (95.0) should be first, then Alice (80.0)
    assert items[0]["full_name"] == "Charlie Brown"
    assert items[1]["full_name"] == "Alice Smith"

    # --- Test 10: Deterministic Sorting by Experience ascending ---
    res = await client.get("/api/v1/candidates?sort_by=experience&sort_order=asc", headers=headers)
    assert res.status_code == 200
    items = res.json()["items"]
    # Diana (2.0), Bob (4.0), Alice (8.0), Charlie (12.0)
    assert items[0]["full_name"] == "Diana Prince"
    assert items[-1]["full_name"] == "Charlie Brown"
