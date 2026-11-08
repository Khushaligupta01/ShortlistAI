from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate, CandidateSkill
from app.models.requisition import Requisition
from app.models.resume import Resume, UploadBatch
from app.services.worker_service import ResumeWorkerService
from tests.conftest import TestSessionLocal, auth_headers, seed_user_with_org

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "resumes"


@pytest.mark.asyncio
async def test_complete_upload_parsing_review_flow(client: AsyncClient, db_session: AsyncSession):
    recruiter, org = await seed_user_with_org(
        db_session, email="flow_recruiter@example.com", password="Password123!", role="recruiter"
    )
    headers = auth_headers(recruiter.id, "recruiter", org.id)

    # 1. Create Requisition
    req = Requisition(
        organization_id=org.id,
        created_by=recruiter.id,
        title="Senior Backend",
        job_description="Senior Backend Engineer with Java and Python",
        status="active",
    )
    db_session.add(req)
    await db_session.commit()

    # 2. Upload 3 files: 1 PDF, 1 DOCX, 1 Malformed
    f1 = (FIXTURES_DIR / "01_strong_java_senior.pdf").read_bytes()
    f2 = (FIXTURES_DIR / "02_partial_java_developer.docx").read_bytes()
    f3 = (FIXTURES_DIR / "08_malformed.pdf").read_bytes()

    upload_payload = [
        ("files", ("01_strong_java_senior.pdf", f1, "application/pdf")),
        ("files", ("02_partial_java_developer.docx", f2, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
        ("files", ("08_malformed.pdf", f3, "application/pdf")),
    ]

    up_resp = await client.post(
        f"/api/v1/requisitions/{req.id}/resumes/upload",
        files=upload_payload,
        headers=headers,
    )
    assert up_resp.status_code == 201
    batch_data = up_resp.json()
    assert batch_data["total_files"] == 3
    batch_id = batch_data["id"]

    # 3. Synchronously run worker to process the batch jobs
    test_worker = ResumeWorkerService(concurrency=2, session_factory=TestSessionLocal)
    await test_worker.process_batch_jobs(uuid.UUID(batch_id))

    # 4. Check Batch Status
    b_resp = await client.get(f"/api/v1/resume-batches/{batch_id}", headers=headers)
    assert b_resp.status_code == 200
    updated_batch = b_resp.json()
    assert updated_batch["total_files"] == 3
    assert updated_batch["completed_files"] >= 1

    # 5. Check Files List
    files_resp = await client.get(f"/api/v1/resume-batches/{batch_id}/files", headers=headers)
    assert files_resp.status_code == 200
    file_items = files_resp.json()
    assert len(file_items) == 3

    parsed_item = next(f for f in file_items if f["file_name"] == "01_strong_java_senior.pdf")
    assert parsed_item["parse_status"] == "parsed"
    assert parsed_item["candidate_id"] is not None
    resume_id = parsed_item["id"]
    candidate_id = parsed_item["candidate_id"]

    # 6. Check Resume Detail
    det_resp = await client.get(f"/api/v1/resumes/{resume_id}", headers=headers)
    assert det_resp.status_code == 200
    detail = det_resp.json()
    assert "Aarav Sharma" in detail["raw_text"]

    # 7. Check Candidate Detail
    cand_resp = await client.get(f"/api/v1/candidates/{candidate_id}", headers=headers)
    assert cand_resp.status_code == 200
    cand_data = cand_resp.json()
    assert cand_data["full_name"] == "Aarav Sharma"
    assert cand_data["email"] == "aarav.sharma@example.com"
    assert cand_data["notice_period_days"] == 30

    # 8. Check Candidate List with Search and Filter
    list_resp = await client.get(f"/api/v1/candidates?search=Aarav", headers=headers)
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] >= 1
    assert any(c["full_name"] == "Aarav Sharma" for c in list_data["items"])

    # 9. Recruiter Review & Correction
    review_resp = await client.post(
        f"/api/v1/resumes/{resume_id}/review",
        json={
            "full_name": "Aarav K. Sharma",
            "location": "San Francisco, CA",
            "notice_period_days": 15,
            "skills": ["Java", "Spring Boot", "Kafka", "Golang"],
        },
        headers=headers,
    )
    assert review_resp.status_code == 200
    reviewed_res = review_resp.json()
    assert reviewed_res["parse_status"] == "parsed"

    # Verify candidate updated
    cand_after = await client.get(f"/api/v1/candidates/{candidate_id}", headers=headers)
    c_updated = cand_after.json()
    assert c_updated["full_name"] == "Aarav K. Sharma"
    assert c_updated["location"] == "San Francisco, CA"
    assert c_updated["notice_period_days"] == 15
    assert any(s["name"] == "golang" for s in c_updated["skills"])
