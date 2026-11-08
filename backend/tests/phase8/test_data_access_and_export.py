from __future__ import annotations

import json
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate, CandidateEmployment, CandidateEducation, CandidateSkill
from app.models.evaluation import Evaluation
from app.models.resume import Resume
from app.models.audit import ConsentRecord
from tests.conftest import auth_headers, create_test_org, seed_user_with_org


@pytest.mark.asyncio
async def test_data_access_and_export_lifecycle(client: AsyncClient, db_session: AsyncSession):
    # Setup Recruiter & Staffing Org
    recruiter, org = await seed_user_with_org(
        db_session, email="rec_export@staffing.com", password="Password123!", role="recruiter", org_name="Apex Export Org"
    )
    recruiter_headers = auth_headers(recruiter.id, "recruiter", org.id)

    # Candidate with complete profile
    candidate = Candidate(
        id=uuid.uuid4(),
        organization_id=org.id,
        full_name="Jonathan Archer",
        email="j.archer@starfleet.org",
        phone="+15551234567",
        location="San Francisco, CA",
        total_experience_years=10.0,
        notice_period_days=30,
        consent_status="GRANTED",
    )
    db_session.add(candidate)
    await db_session.flush()

    # Add employment
    emp = CandidateEmployment(
        id=uuid.uuid4(),
        candidate_id=candidate.id,
        company="Starfleet Command",
        job_title="Captain",
        start_date="2151",
        end_date="2161",
        is_current=True,
        description="Commanded NX-01 exploration mission.",
        technologies=["Warp Propulsion", "Phase Pistols"],
    )
    db_session.add(emp)

    # Add skill
    sk = CandidateSkill(
        id=uuid.uuid4(),
        candidate_id=candidate.id,
        name="Warp Propulsion",
        raw_name="Warp Drive Systems",
        evidence="10 years commanding warp 5 starship.",
    )
    db_session.add(sk)

    # Add resume
    res = Resume(
        id=uuid.uuid4(),
        candidate_id=candidate.id,
        organization_id=org.id,
        file_name="archer_cv.pdf",
        storage_path="data/resumes/dummy_cv.pdf",
        mime_type="application/pdf",
        file_size_bytes=2048,
        parse_status="parsed",
    )
    db_session.add(res)

    # Add consent record
    cr = ConsentRecord(
        id=uuid.uuid4(),
        candidate_id=candidate.id,
        organization_id=org.id,
        uploaded_by=recruiter.id,
        legal_basis="CONSENT",
        status="GRANTED",
        purpose="deep_space_recruitment",
        version="v1.0",
        collection_method="DIRECT_NOTICE",
        privacy_notice_acknowledged=True,
    )
    db_session.add(cr)
    await db_session.commit()

    # 1. Create Data Access/Export Request
    req_res = await client.post(
        f"/api/v1/candidates/{candidate.id}/data-requests",
        headers=recruiter_headers,
        json={
            "request_type": "EXPORT",
            "reason": "Candidate requested copy of all stored personal records.",
        },
    )
    assert req_res.status_code == 201, req_res.text
    req_data = req_res.json()
    request_id = req_data["id"]
    assert req_data["status"] == "PENDING"

    # 2. List Data Requests
    list_res = await client.get("/api/v1/data-requests", headers=recruiter_headers)
    assert list_res.status_code == 200
    assert any(item["id"] == request_id for item in list_res.json()["items"])

    # 3. Generate JSON Export
    export_gen_res = await client.post(
        f"/api/v1/data-requests/{request_id}/export",
        headers=recruiter_headers,
    )
    assert export_gen_res.status_code == 200, export_gen_res.text
    export_data = export_gen_res.json()

    # Verify candidate personal data is present
    assert export_data["profile"]["full_name"] == "Jonathan Archer"
    assert export_data["profile"]["email"] == "j.archer@starfleet.org"
    assert len(export_data["employments"]) == 1
    assert export_data["employments"][0]["company"] == "Starfleet Command"
    assert len(export_data["skills"]) == 1
    assert export_data["skills"][0]["name"] == "Warp Propulsion"
    assert len(export_data["consent_history"]) == 1
    assert "excluded_fields_notice" in export_data

    # Verify sensitive data strictly EXCLUDED:
    export_json_str = json.dumps(export_data).lower()
    assert "password_hash" not in export_json_str
    assert "secret_key" not in export_json_str
    assert "dummy_cv.pdf" not in export_json_str  # Server disk storage paths stripped from resume metadata

    # 4. Download Export File
    download_res = await client.get(
        f"/api/v1/data-exports/{request_id}",
        headers=recruiter_headers,
    )
    assert download_res.status_code == 200
    assert download_res.headers.get("content-type") == "application/json"
    downloaded_json = json.loads(download_res.text)
    assert downloaded_json["candidate_id"] == str(candidate.id)


@pytest.mark.asyncio
async def test_data_export_cross_organization_isolation(client: AsyncClient, db_session: AsyncSession):
    recruiter_a, org_a = await seed_user_with_org(
        db_session, email="rec_a_exp_iso@staffing.com", password="Password123!", role="recruiter", org_name="Org A Export Iso"
    )
    headers_a = auth_headers(recruiter_a.id, "recruiter", org_a.id)

    recruiter_b, org_b = await seed_user_with_org(
        db_session, email="rec_b_exp_iso@staffing.com", password="Password123!", role="recruiter", org_name="Org B Export Iso"
    )
    headers_b = auth_headers(recruiter_b.id, "recruiter", org_b.id)

    # Candidate belongs to Org A
    cand_a = Candidate(
        id=uuid.uuid4(),
        organization_id=org_a.id,
        full_name="Secret Agent A",
        email="agent_a@org-a.com",
    )
    db_session.add(cand_a)
    await db_session.commit()

    # Recruiter B tries to request export of Candidate A -> 404
    cross_res = await client.post(
        f"/api/v1/candidates/{cand_a.id}/data-requests",
        headers=headers_b,
        json={"request_type": "EXPORT"},
    )
    assert cross_res.status_code == 404
