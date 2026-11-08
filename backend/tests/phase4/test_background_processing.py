from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.organization import Organization
from app.models.requisition import Requisition
from app.models.resume import Resume, ResumeProcessingJob, UploadBatch
from app.services.storage_service import get_storage_service
from app.services.worker_service import ResumeWorkerService
from tests.conftest import TestSessionLocal, create_test_org, create_test_user

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "resumes"


@pytest.fixture
def test_worker():
    return ResumeWorkerService(concurrency=2, lock_timeout_seconds=60, session_factory=TestSessionLocal)


@pytest.mark.asyncio
async def test_job_claiming_and_execution_lifecycle(db_session: AsyncSession, test_worker: ResumeWorkerService):
    await db_session.execute(delete(ResumeProcessingJob))
    await db_session.commit()

    org = await create_test_org(db_session, name="Worker Test Org")
    user = await create_test_user(db_session, email="worker_user@example.com")

    # Create Requisition
    req = Requisition(
        organization_id=org.id,
        created_by=user.id,
        title="Senior Java Developer",
        job_description="Senior Java Dev with Spring Boot",
        status="active",
    )
    db_session.add(req)
    await db_session.flush()

    # Create UploadBatch
    batch = UploadBatch(
        organization_id=org.id,
        recruiter_id=user.id,
        requisition_id=req.id,
        total_files=1,
        accepted_files=1,
        status="processing",
    )
    db_session.add(batch)
    await db_session.flush()

    # Save file in storage
    storage = get_storage_service()
    pdf_bytes = (FIXTURES_DIR / "01_strong_java_senior.pdf").read_bytes()
    storage_key = await storage.save_file(org.id, pdf_bytes, ".pdf")

    # Create Resume
    resume = Resume(
        organization_id=org.id,
        requisition_id=req.id,
        uploaded_by=user.id,
        file_name="01_strong_java_senior.pdf",
        storage_path=storage_key,
        mime_type="application/pdf",
        file_size_bytes=len(pdf_bytes),
        parse_status="pending",
        extraction_status="pending",
        upload_batch_id=batch.id,
    )
    db_session.add(resume)
    await db_session.flush()

    # Create Job
    job = ResumeProcessingJob(
        resume_id=resume.id,
        batch_id=batch.id,
        organization_id=org.id,
        status="pending",
    )
    db_session.add(job)
    await db_session.commit()

    # 1. Test Claim Job
    claimed = await test_worker.claim_next_job(db_session, worker_id="test-worker-1")
    assert claimed is not None
    assert claimed.id == job.id
    assert claimed.status == "processing"
    assert claimed.attempt_count == 1
    assert claimed.lock_id == "test-worker-1"

    # 2. Test Execute Job
    success = await test_worker.execute_job(db_session, claimed)
    assert success is True

    # 3. Verify Job Status
    await db_session.refresh(job)
    assert job.status == "completed"
    assert job.completed_at is not None

    # 4. Verify Resume Status & Candidate Creation
    await db_session.refresh(resume)
    assert resume.parse_status == "parsed"
    assert resume.extraction_status == "extracted"
    assert resume.candidate_id is not None
    assert "Aarav Sharma" in (resume.raw_text or "")

    # Verify Candidate Record
    c_res = await db_session.execute(select(Candidate).where(Candidate.id == resume.candidate_id))
    cand = c_res.scalars().first()
    assert cand is not None
    assert cand.email == "aarav.sharma@example.com"
    assert cand.notice_period_days == 30

    # 5. Verify Batch Aggregation
    await db_session.refresh(batch)
    assert batch.completed_files == 1
    assert batch.failed_files == 0
    assert batch.status == "completed"


@pytest.mark.asyncio
async def test_job_retry_on_corrupted_file(db_session: AsyncSession, test_worker: ResumeWorkerService):
    org = await create_test_org(db_session, name="Retry Test Org")
    user = await create_test_user(db_session, email="retry_user@example.com")

    req = Requisition(
        organization_id=org.id,
        created_by=user.id,
        title="Python Dev",
        job_description="Python Dev JD",
        status="active",
    )
    db_session.add(req)
    await db_session.flush()

    batch = UploadBatch(
        organization_id=org.id,
        recruiter_id=user.id,
        requisition_id=req.id,
        total_files=1,
        accepted_files=1,
        status="processing",
    )
    db_session.add(batch)
    await db_session.flush()

    # Save malformed PDF
    storage = get_storage_service()
    bad_bytes = (FIXTURES_DIR / "08_malformed.pdf").read_bytes()
    storage_key = await storage.save_file(org.id, bad_bytes, ".pdf")

    resume = Resume(
        organization_id=org.id,
        requisition_id=req.id,
        file_name="08_malformed.pdf",
        storage_path=storage_key,
        mime_type="application/pdf",
        file_size_bytes=len(bad_bytes),
        parse_status="pending",
        extraction_status="pending",
        upload_batch_id=batch.id,
    )
    db_session.add(resume)
    await db_session.flush()

    job = ResumeProcessingJob(
        resume_id=resume.id,
        batch_id=batch.id,
        organization_id=org.id,
        status="pending",
        max_attempts=2,
    )
    db_session.add(job)
    await db_session.commit()

    # Execute job
    await test_worker.execute_job(db_session, job)

    await db_session.refresh(resume)
    assert resume.parse_status == "failed"
    assert resume.error_code in ("CORRUPTED_PDF", "EXTRACTION_FAILED")

    await db_session.refresh(batch)
    assert batch.failed_files == 1
    assert batch.status == "failed"
