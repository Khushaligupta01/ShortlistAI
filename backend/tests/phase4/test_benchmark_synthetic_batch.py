from __future__ import annotations

import time
import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.requisition import Requisition
from app.services.worker_service import ResumeWorkerService
from tests.conftest import TestSessionLocal, auth_headers, seed_user_with_org

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "resumes"


@pytest.mark.asyncio
async def test_bulk_batch_processing_benchmark(client: AsyncClient, db_session: AsyncSession):
    """
    Measures actual ingestion, storage, extraction, parsing, and candidate creation
    throughput on a synthetic batch of 20 documents.
    """
    recruiter, org = await seed_user_with_org(
        db_session, email="bench_recruiter@example.com", password="Password123!", role="recruiter"
    )
    headers = auth_headers(recruiter.id, "recruiter", org.id)

    req = Requisition(
        organization_id=org.id,
        created_by=recruiter.id,
        title="Benchmark Req",
        job_description="Benchmark Job Description",
        status="active",
    )
    db_session.add(req)
    await db_session.commit()

    # Prepare batch of 20 resumes (mix of PDF and DOCX)
    pdf_bytes = (FIXTURES_DIR / "01_strong_java_senior.pdf").read_bytes()
    docx_bytes = (FIXTURES_DIR / "02_partial_java_developer.docx").read_bytes()

    batch_files = []
    for i in range(10):
        batch_files.append(("files", (f"bench_java_senior_{i}.pdf", pdf_bytes, "application/pdf")))
        batch_files.append((
            "files",
            (f"bench_java_mid_{i}.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ))

    t0_upload = time.perf_counter()
    resp = await client.post(
        f"/api/v1/requisitions/{req.id}/resumes/upload",
        files=batch_files,
        headers=headers,
    )
    t_upload = time.perf_counter() - t0_upload

    assert resp.status_code == 201
    batch_data = resp.json()
    batch_id = uuid.UUID(batch_data["id"])
    assert batch_data["total_files"] == 20

    # Process all 20 jobs with concurrency=5
    test_worker = ResumeWorkerService(concurrency=5, session_factory=TestSessionLocal)

    t0_process = time.perf_counter()
    await test_worker.process_batch_jobs(batch_id)
    t_process = time.perf_counter() - t0_process

    # Fetch final batch stats
    b_resp = await client.get(f"/api/v1/resume-batches/{batch_id}", headers=headers)
    assert b_resp.status_code == 200
    final_stats = b_resp.json()

    throughput_docs_per_sec = 20 / t_process if t_process > 0 else 0

    print(f"\n--- Phase 4 Bulk Processing Benchmark (20 Documents) ---")
    print(f"Upload & Validation Time: {t_upload:.3f} s")
    print(f"Worker Processing Time:   {t_process:.3f} s")
    print(f"End-to-End Throughput:    {throughput_docs_per_sec:.2f} docs/sec")
    print(f"Completed Files:          {final_stats['completed_files']}")
    print(f"Duplicate Files:          {final_stats['duplicate_files']}")
    print(f"Failed Files:             {final_stats['failed_files']}")

    assert final_stats["completed_files"] + final_stats["duplicate_files"] >= 1
