from __future__ import annotations

import io
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.requisition import Requisition
from app.models.resume import Resume, UploadBatch
from app.services.storage_service import get_storage_service
from tests.conftest import auth_headers, seed_user_with_org

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "resumes"


@pytest.mark.asyncio
async def test_recruiter_can_upload_and_download(client: AsyncClient, db_session: AsyncSession):
    recruiter, org = await seed_user_with_org(
        db_session, email="recruiter_auth@example.com", password="Password123!", role="recruiter"
    )
    headers = auth_headers(recruiter.id, "recruiter", org.id)

    # Create Requisition
    req = Requisition(
        organization_id=org.id,
        created_by=recruiter.id,
        title="Java Dev",
        job_description="Java Developer JD",
        status="active",
    )
    db_session.add(req)
    await db_session.commit()

    # Upload valid PDF
    pdf_path = FIXTURES_DIR / "01_strong_java_senior.pdf"
    files = [("files", ("01_strong_java_senior.pdf", pdf_path.read_bytes(), "application/pdf"))]

    resp = await client.post(
        f"/api/v1/requisitions/{req.id}/resumes/upload",
        files=files,
        headers=headers,
    )
    assert resp.status_code == 201
    batch_data = resp.json()
    batch_id = batch_data["id"]

    # Get batch files
    f_resp = await client.get(f"/api/v1/resume-batches/{batch_id}/files", headers=headers)
    assert f_resp.status_code == 200
    file_list = f_resp.json()
    assert len(file_list) == 1
    resume_id = file_list[0]["id"]

    # Recruiter can download resume document
    d_resp = await client.get(f"/api/v1/resumes/{resume_id}/download", headers=headers)
    assert d_resp.status_code == 200
    assert len(d_resp.content) > 0


@pytest.mark.asyncio
async def test_client_cannot_download_raw_resume(client: AsyncClient, db_session: AsyncSession):
    # Recruiter uploads resume in staffing firm
    recruiter, staff_org = await seed_user_with_org(
        db_session, email="recruiter_priv@example.com", password="Password123!", role="recruiter"
    )
    client_user, client_org = await seed_user_with_org(
        db_session, email="client_hm@example.com", password="Password123!", role="client_hiring_manager"
    )

    rec_headers = auth_headers(recruiter.id, "recruiter", staff_org.id)
    client_headers = auth_headers(client_user.id, "client_hiring_manager", staff_org.id)

    req = Requisition(
        organization_id=staff_org.id,
        created_by=recruiter.id,
        title="React Dev",
        job_description="React Developer JD",
        status="active",
    )
    db_session.add(req)
    await db_session.commit()

    pdf_path = FIXTURES_DIR / "01_strong_java_senior.pdf"
    files = [("files", ("01_strong_java_senior.pdf", pdf_path.read_bytes(), "application/pdf"))]
    resp = await client.post(f"/api/v1/requisitions/{req.id}/resumes/upload", files=files, headers=rec_headers)
    batch_id = resp.json()["id"]

    f_resp = await client.get(f"/api/v1/resume-batches/{batch_id}/files", headers=rec_headers)
    resume_id = f_resp.json()[0]["id"]

    # Client attempts to download raw resume document -> MUST BE 403 Forbidden
    down_resp = await client.get(f"/api/v1/resumes/{resume_id}/download", headers=client_headers)
    assert down_resp.status_code == 403


@pytest.mark.asyncio
async def test_client_contact_details_masked(client: AsyncClient, db_session: AsyncSession):
    from tests.conftest import create_membership

    recruiter, staff_org = await seed_user_with_org(
        db_session, email="rec_mask@example.com", password="Password123!", role="recruiter"
    )
    client_user, _ = await seed_user_with_org(
        db_session, email="client_mask@example.com", password="Password123!", role="client_hiring_manager"
    )
    # Associate client user with the staffing org as client_hiring_manager
    await create_membership(db_session, client_user.id, staff_org.id, role="client_hiring_manager")
    await db_session.commit()

    # Candidate with sensitive contact details
    candidate = Candidate(
        organization_id=staff_org.id,
        full_name="Confidential Candidate",
        email="confidential.direct@personal.com",
        phone="+1-555-999-0000",
        location="New York, NY",
    )
    db_session.add(candidate)
    await db_session.commit()

    # Client requests candidate details -> email and phone must be masked
    client_headers = auth_headers(client_user.id, "client_hiring_manager", staff_org.id)
    resp = await client.get(f"/api/v1/candidates/{candidate.id}", headers=client_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["full_name"] == "Confidential Candidate"
    assert "Protected" in data["email"]
    assert "Protected" in data["phone"]


@pytest.mark.asyncio
async def test_cross_organization_data_isolation(client: AsyncClient, db_session: AsyncSession):
    recruiter_a, org_a = await seed_user_with_org(
        db_session, email="rec_a@example.com", password="Password123!", role="recruiter", org_name="Firm A"
    )
    recruiter_b, org_b = await seed_user_with_org(
        db_session, email="rec_b@example.com", password="Password123!", role="recruiter", org_name="Firm B"
    )

    headers_a = auth_headers(recruiter_a.id, "recruiter", org_a.id)
    headers_b = auth_headers(recruiter_b.id, "recruiter", org_b.id)

    # Org A creates requisition and upload
    req_a = Requisition(
        organization_id=org_a.id,
        created_by=recruiter_a.id,
        title="Firm A Job",
        job_description="Firm A JD",
        status="active",
    )
    db_session.add(req_a)
    await db_session.commit()

    pdf_path = FIXTURES_DIR / "01_strong_java_senior.pdf"
    files = [("files", ("01_strong_java_senior.pdf", pdf_path.read_bytes(), "application/pdf"))]
    resp_a = await client.post(f"/api/v1/requisitions/{req_a.id}/resumes/upload", files=files, headers=headers_a)
    batch_a_id = resp_a.json()["id"]

    # Recruiter B tries to upload to Org A's requisition -> 403 Forbidden
    files_b = [("files", ("01_strong_java_senior.pdf", pdf_path.read_bytes(), "application/pdf"))]
    resp_b_upload = await client.post(f"/api/v1/requisitions/{req_a.id}/resumes/upload", files=files_b, headers=headers_b)
    assert resp_b_upload.status_code == 403

    # Recruiter B tries to get Org A's batch -> 403 Forbidden
    resp_b_batch = await client.get(f"/api/v1/resume-batches/{batch_a_id}", headers=headers_b)
    assert resp_b_batch.status_code == 403
