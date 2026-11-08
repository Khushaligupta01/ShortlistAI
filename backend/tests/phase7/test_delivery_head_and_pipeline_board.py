from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.evaluation import Evaluation
from app.models.requisition import Requisition
from app.models.scorecard import Scorecard
from app.models.submission import Submission
from tests.conftest import auth_headers, create_test_org, seed_user_with_org


@pytest.mark.asyncio
async def test_delivery_head_pipeline_summary_and_tenant_boundary(client: AsyncClient, db_session: AsyncSession):
    # 1. Staffing Firm 1: Delivery Head and Recruiter
    delivery_head, staffing_org_1 = await seed_user_with_org(
        db_session, email="dh_apex@apex.com", password="Password123!", role="delivery_head", org_name="Apex Staffing Solutions"
    )
    dh_headers = auth_headers(delivery_head.id, "delivery_head", staffing_org_1.id)

    recruiter_1, _ = await seed_user_with_org(
        db_session, email="rec_apex@apex.com", password="Password123!", role="recruiter", org_name="Apex Staffing Solutions"
    )
    recruiter_headers = auth_headers(recruiter_1.id, "recruiter", staffing_org_1.id)

    # 2. Staffing Firm 2: Delivery Head 2 (Tenant boundary test)
    dh_2, staffing_org_2 = await seed_user_with_org(
        db_session, email="dh_other@other.com", password="Password123!", role="delivery_head", org_name="Other Staffing Corp"
    )
    dh_2_headers = auth_headers(dh_2.id, "delivery_head", staffing_org_2.id)

    # 3. Client Organization
    client_corp = await create_test_org(db_session, name="Stripe Fintech Client", org_type="client_company")

    # 4. Requisition for Staffing Firm 1
    req = Requisition(
        id=uuid.uuid4(),
        organization_id=staffing_org_1.id,
        created_by=recruiter_1.id,
        title="Principal Infrastructure Engineer",
        job_description="Distributed consensus and cloud reliability.",
        status="active",
        client_organization_id=client_corp.id,
    )
    db_session.add(req)
    await db_session.commit()

    sc = Scorecard(id=uuid.uuid4(), requisition_id=req.id, status="approved", version_number=1)
    db_session.add(sc)
    await db_session.commit()

    # 5. Create 3 candidates with different outcomes: 1 Hired, 1 Shortlisted, 1 Submitted
    candidates = []
    for i, name in enumerate(["Ada Lovelace", "Charles Babbage", "John von Neumann"]):
        c = Candidate(
            id=uuid.uuid4(),
            organization_id=staffing_org_1.id,
            full_name=name,
            email=f"{name.lower().replace(' ', '.')}@computing.org",
            total_experience_years=10.0 + i,
        )
        db_session.add(c)
        await db_session.commit()

        ev = Evaluation(
            id=uuid.uuid4(),
            candidate_id=c.id,
            requisition_id=req.id,
            scorecard_id=sc.id,
            scorecard_version=1,
            total_score=90.0 + i,
            raw_score=90.0 + i,
            normalized_score=90.0 + i,
            evaluation_status="completed",
        )
        db_session.add(ev)
        await db_session.commit()

        candidates.append((c, ev))

    # Candidate 0: Hired
    sub_0 = Submission(
        id=uuid.uuid4(),
        candidate_id=candidates[0][0].id,
        requisition_id=req.id,
        evaluation_id=candidates[0][1].id,
        submitted_by=recruiter_1.id,
        source_organization_id=staffing_org_1.id,
        client_organization_id=client_corp.id,
        status="active",
        current_stage="HIRED",
    )
    # Candidate 1: Shortlisted
    sub_1 = Submission(
        id=uuid.uuid4(),
        candidate_id=candidates[1][0].id,
        requisition_id=req.id,
        evaluation_id=candidates[1][1].id,
        submitted_by=recruiter_1.id,
        source_organization_id=staffing_org_1.id,
        client_organization_id=client_corp.id,
        status="active",
        current_stage="CLIENT_SHORTLISTED",
    )
    # Candidate 2: Submitted
    sub_2 = Submission(
        id=uuid.uuid4(),
        candidate_id=candidates[2][0].id,
        requisition_id=req.id,
        evaluation_id=candidates[2][1].id,
        submitted_by=recruiter_1.id,
        source_organization_id=staffing_org_1.id,
        client_organization_id=client_corp.id,
        status="active",
        current_stage="SUBMITTED",
    )
    db_session.add_all([sub_0, sub_1, sub_2])
    await db_session.commit()

    # 6. Recruiter cannot access Delivery Head overview (RBAC check)
    rec_res = await client.get("/api/v1/delivery/pipeline-summary", headers=recruiter_headers)
    assert rec_res.status_code == 403

    # 7. Delivery Head 1 queries pipeline summary
    dh_res = await client.get("/api/v1/delivery/pipeline-summary", headers=dh_headers)
    assert dh_res.status_code == 200
    dh_data = dh_res.json()
    assert dh_data["total_submissions"] == 3
    # 2 are shortlisted or hired (both count towards shortlist funnel)
    assert dh_data["conversion_shortlist_rate"] == 66.7
    assert dh_data["conversion_hire_rate"] == 33.3

    assert len(dh_data["clients"]) == 1
    client_entry = dh_data["clients"][0]
    assert client_entry["client_organization_name"] == "Stripe Fintech Client"
    assert client_entry["total_submissions"] == 3
    assert client_entry["hired_count"] == 1

    # 8. Tenant Isolation: Delivery Head 2 sees 0 submissions
    dh_2_res = await client.get("/api/v1/delivery/pipeline-summary", headers=dh_2_headers)
    assert dh_2_res.status_code == 200
    assert dh_2_res.json()["total_submissions"] == 0
    assert len(dh_2_res.json()["clients"]) == 0
