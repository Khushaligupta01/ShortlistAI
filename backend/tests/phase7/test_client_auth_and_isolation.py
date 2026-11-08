from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.evaluation import Evaluation
from app.models.organization import Organization
from app.models.requisition import Requisition
from app.models.scorecard import Scorecard
from app.models.submission import Submission
from tests.conftest import auth_headers, create_test_org, seed_user_with_org


@pytest.mark.asyncio
async def test_client_portal_access_and_tenant_isolation(client: AsyncClient, db_session: AsyncSession):
    # 1. Setup Staffing Firm with Recruiter
    recruiter, staffing_org = await seed_user_with_org(
        db_session, email="recruiter_iso@staffing.com", password="Password123!", role="recruiter", org_name="Apex Staffing"
    )
    recruiter_headers = auth_headers(recruiter.id, "recruiter", staffing_org.id)

    # 2. Setup Client A with Hiring Manager A
    client_org_a = await create_test_org(db_session, name="Acme Corp Client A", org_type="client_company")
    client_user_a, _ = await seed_user_with_org(
        db_session, email="client_a@acme.com", password="Password123!", role="client_hiring_manager", org_name="Acme Corp Client A"
    )
    # Update client_user_a's organization membership to client_org_a
    client_a_headers = auth_headers(client_user_a.id, "client_hiring_manager", client_org_a.id)

    # 3. Setup Client B with Hiring Manager B
    client_org_b = await create_test_org(db_session, name="Beta Inc Client B", org_type="client_company")
    client_user_b, _ = await seed_user_with_org(
        db_session, email="client_b@beta.com", password="Password123!", role="client_hiring_manager", org_name="Beta Inc Client B"
    )
    client_b_headers = auth_headers(client_user_b.id, "client_hiring_manager", client_org_b.id)

    # 4. Create Requisition in Staffing Org shared with Client A
    req = Requisition(
        id=uuid.uuid4(),
        organization_id=staffing_org.id,
        created_by=recruiter.id,
        title="Senior Cloud Architect",
        job_description="Looking for senior cloud architect with AWS and Python.",
        status="active",
        client_organization_id=client_org_a.id,
    )
    db_session.add(req)
    await db_session.commit()

    # Create Scorecard and Candidate
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
        full_name="Alan Turing",
        email="alan@turing.org",
        total_experience_years=10.0,
    )
    db_session.add(cand)
    await db_session.commit()

    eval_obj = Evaluation(
        id=uuid.uuid4(),
        candidate_id=cand.id,
        requisition_id=req.id,
        scorecard_id=sc.id,
        scorecard_version=1,
        total_score=92.5,
        raw_score=92.5,
        normalized_score=92.5,
        confidence_level="HIGH",
        evaluation_status="completed",
    )
    db_session.add(eval_obj)
    await db_session.commit()

    # 5. Recruiter submits candidate to Client A
    sub_payload = {
        "candidate_id": str(cand.id),
        "client_organization_id": str(client_org_a.id),
        "recruiter_notes_for_client": "Exceptional fit with proven distributed systems experience.",
    }
    sub_res = await client.post(
        f"/api/v1/requisitions/{req.id}/submissions",
        json=sub_payload,
        headers=recruiter_headers,
    )
    assert sub_res.status_code == 201
    submission_data = sub_res.json()
    submission_id = submission_data["submission_id"]

    # 6. Verify Client A can access dashboard, requisitions, and the submission
    dash_a = await client.get("/api/v1/client/dashboard", headers=client_a_headers)
    assert dash_a.status_code == 200
    assert dash_a.json()["total_submissions_count"] == 1
    assert dash_a.json()["awaiting_review_count"] == 1

    subs_a = await client.get("/api/v1/client/submissions", headers=client_a_headers)
    assert subs_a.status_code == 200
    items_a = subs_a.json()
    assert len(items_a) == 1
    assert items_a[0]["submission_id"] == submission_id

    # Client A views detail
    detail_a = await client.get(f"/api/v1/client/submissions/{submission_id}", headers=client_a_headers)
    assert detail_a.status_code == 200
    assert detail_a.json()["candidate_reference"] == submission_data["candidate_reference"]

    # 7. Verify Client B CANNOT view Client A's submission (STRICT TENANT ISOLATION)
    subs_b = await client.get("/api/v1/client/submissions", headers=client_b_headers)
    assert subs_b.status_code == 200
    assert len(subs_b.json()) == 0

    detail_b = await client.get(f"/api/v1/client/submissions/{submission_id}", headers=client_b_headers)
    assert detail_b.status_code in [403, 404]

    # Client B CANNOT submit decision on Client A's candidate
    dec_b = await client.post(
        f"/api/v1/client/submissions/{submission_id}/decisions",
        json={"decision": "CLIENT_SHORTLISTED"},
        headers=client_b_headers,
    )
    assert dec_b.status_code in [403, 404]

    # 8. Verify Client user CANNOT call recruiter submission endpoint (Role enforcement)
    unauth_sub = await client.post(
        f"/api/v1/requisitions/{req.id}/submissions",
        json=sub_payload,
        headers=client_a_headers,
    )
    assert unauth_sub.status_code == 403
