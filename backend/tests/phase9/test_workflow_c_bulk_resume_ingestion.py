from __future__ import annotations

import uuid
from pathlib import Path
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.candidate import Candidate
from app.models.requisition import Requisition
from app.models.resume import Resume, UploadBatch
from app.services.worker_service import ResumeWorkerService
from tests.conftest import TestSessionLocal, auth_headers, seed_user_with_org

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "resumes"


@pytest.mark.asyncio
async def test_workflow_c_bulk_resume_ingestion(client: AsyncClient, db_session: AsyncSession):
    """
    Workflow C:
    1. Create Requisition.
    2. Test file validation:
       - Unsupported extension (.exe) rejected.
       - Corrupt/empty payload handled.
    3. Bulk upload multiple synthetic PDF and DOCX files.
    4. Worker claims and executes processing jobs.
    5. Verify structured candidate profile extraction.
    6. Verify exact file duplicate detection.
    """
    recruiter, org = await seed_user_with_org(
        db_session,
        email="recruiter.ingest@example.com",
        password="PassWord123!",
        role="recruiter",
        org_name="Ingestion Staffing Corp",
    )
    headers = auth_headers(recruiter.id, "recruiter", org.id)

    # 1. Create Requisition
    req = Requisition(
        organization_id=org.id,
        created_by=recruiter.id,
        title="Full Stack Engineer",
        job_description="Python, FastAPI, React",
        status="active",
    )
    db_session.add(req)
    await db_session.commit()

    # 2. Unsupported extension rejection (.exe) handled cleanly in batch validation
    invalid_files = [
        ("files", ("malicious.exe", b"MZ\x90\x00\x03\x00\x00\x00", "application/x-msdownload")),
    ]
    invalid_res = await client.post(
        f"/api/v1/requisitions/{req.id}/resumes/upload",
        files=invalid_files,
        headers=headers,
    )
    assert invalid_res.status_code == 201
    invalid_batch = invalid_res.json()
    assert invalid_batch["failed_files"] >= 1 or invalid_batch["rejected_files"] >= 1

    # Empty payload validation
    empty_res = await client.post(
        f"/api/v1/requisitions/{req.id}/resumes/upload",
        headers=headers,
    )
    assert empty_res.status_code in (400, 422)

    # 3. Valid bulk upload (PDF, DOCX, and malformed PDF to verify error capture)
    f1 = (FIXTURES_DIR / "01_strong_java_senior.pdf").read_bytes()
    f2 = (FIXTURES_DIR / "02_partial_java_developer.docx").read_bytes()
    f3 = (FIXTURES_DIR / "08_malformed.pdf").read_bytes()

    upload_payload = [
        ("files", ("01_strong_java_senior.pdf", f1, "application/pdf")),
        ("files", ("02_partial_java_developer.docx", f2, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
        ("files", ("08_malformed.pdf", f3, "application/pdf")),
    ]

    up_res = await client.post(
        f"/api/v1/requisitions/{req.id}/resumes/upload",
        files=upload_payload,
        headers=headers,
    )
    assert up_res.status_code == 201, up_res.text
    batch_data = up_res.json()
    assert batch_data["total_files"] == 3
    batch_id = uuid.UUID(batch_data["id"])

    # 4. Background worker executes jobs
    worker = ResumeWorkerService(concurrency=2, session_factory=TestSessionLocal)
    await worker.process_batch_jobs(batch_id)

    # Verify batch status reflects completion and failures
    batch_status_res = await client.get(f"/api/v1/resume-batches/{batch_id}", headers=headers)
    assert batch_status_res.status_code == 200
    batch_status = batch_status_res.json()
    assert batch_status["completed_files"] >= 1
    assert batch_status["failed_files"] >= 1

    # 5. Verify candidates created from parsed resumes
    cand_query = await db_session.execute(
        select(Candidate).where(Candidate.organization_id == org.id)
    )
    candidates = list(cand_query.scalars().all())
    assert len(candidates) >= 1

    # 6. Verify duplicate file detection: uploading same PDF again
    dup_payload = [
        ("files", ("01_strong_java_senior.pdf", f1, "application/pdf")),
    ]
    dup_res = await client.post(
        f"/api/v1/requisitions/{req.id}/resumes/upload",
        files=dup_payload,
        headers=headers,
    )
    assert dup_res.status_code == 201
    dup_batch_id = uuid.UUID(dup_res.json()["id"])
    await worker.process_batch_jobs(dup_batch_id)

    dup_files_res = await client.get(f"/api/v1/resume-batches/{dup_batch_id}/files", headers=headers)
    assert dup_files_res.status_code == 200
    dup_files = dup_files_res.json()
    assert len(dup_files) == 1
    assert dup_files[0]["parse_status"] == "duplicate" or dup_files[0]["duplicate_of_id"] is not None
