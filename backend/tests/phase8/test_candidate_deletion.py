from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.candidate import Candidate
from app.models.resume import Resume, ResumeProcessingJob
from app.models.audit import DeletionRequest
from tests.conftest import auth_headers, create_test_org, seed_user_with_org


@pytest.mark.asyncio
async def test_candidate_deletion_lifecycle_and_scrubbing(client: AsyncClient, db_session: AsyncSession):
    # Setup Recruiter, Delivery Head & Staffing Org
    recruiter, org = await seed_user_with_org(
        db_session, email="rec_del@staffing.com", password="Password123!", role="recruiter", org_name="Apex Erasure Org"
    )
    recruiter_headers = auth_headers(recruiter.id, "recruiter", org.id)

    delivery_head, _ = await seed_user_with_org(
        db_session, email="head_del@staffing.com", password="Password123!", role="delivery_head", org_name="Apex Erasure Org"
    )
    dh_headers = auth_headers(delivery_head.id, "delivery_head", org.id)

    # Create temporary resume file on disk to verify physical deletion
    temp_dir = tempfile.mkdtemp()
    temp_file = Path(temp_dir) / "real_resume_to_delete.pdf"
    temp_file.write_bytes(b"%PDF-1.4 dummy resume content for deletion verification")
    assert temp_file.exists()

    # Create candidate
    candidate = Candidate(
        id=uuid.uuid4(),
        organization_id=org.id,
        full_name="Jean-Luc Picard",
        email="picard@enterprise.org",
        phone="+15559876543",
        location="La Barre, France",
        consent_status="GRANTED",
    )
    db_session.add(candidate)
    await db_session.flush()

    # Create resume pointing to temp_file
    resume = Resume(
        id=uuid.uuid4(),
        candidate_id=candidate.id,
        organization_id=org.id,
        file_name="picard_cv.pdf",
        storage_path=str(temp_file),
        mime_type="application/pdf",
        file_size_bytes=len(temp_file.read_bytes()),
        raw_text="Captain of the USS Enterprise.",
        normalized_text="Captain of the USS Enterprise.",
        parse_status="parsed",
    )
    db_session.add(resume)
    await db_session.commit()

    # 1. Recruiter creates Deletion Request
    del_res = await client.post(
        f"/api/v1/candidates/{candidate.id}/deletion-requests",
        headers=recruiter_headers,
        json={"reason": "Candidate exercised right to erasure."},
    )
    assert del_res.status_code == 201, del_res.text
    del_data = del_res.json()
    request_id = del_data["id"]
    assert del_data["status"] == "REQUESTED"

    # 2. Delivery Head puts on Legal Hold
    hold_res = await client.post(
        f"/api/v1/deletion-requests/{request_id}/review",
        headers=dh_headers,
        json={
            "decision": "HOLD",
            "is_legal_hold": True,
            "legal_hold_reason": "Pending compliance inquiry #1701",
        },
    )
    assert hold_res.status_code == 200
    assert hold_res.json()["is_legal_hold"] is True
    assert hold_res.json()["status"] == "UNDER_REVIEW"

    # 3. Attempting to execute deletion during active legal hold MUST fail
    blocked_exec = await client.post(
        f"/api/v1/deletion-requests/{request_id}/execute",
        headers=dh_headers,
    )
    assert blocked_exec.status_code == 400
    err_detail = (blocked_exec.json().get("message") or blocked_exec.json().get("detail") or "").lower()
    assert "legal hold" in err_detail
    # Resume file must still exist
    assert temp_file.exists()

    # 4. Delivery Head approves deletion after legal hold lifted
    approve_res = await client.post(
        f"/api/v1/deletion-requests/{request_id}/review",
        headers=dh_headers,
        json={
            "decision": "APPROVE",
            "is_legal_hold": False,
            "retention_policy_notes": "Legal inquiry concluded; erasure authorized under Policy Sec 9.",
        },
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "APPROVED"

    # 5. Delivery Head executes controlled deletion
    exec_res = await client.post(
        f"/api/v1/deletion-requests/{request_id}/execute",
        headers=dh_headers,
    )
    assert exec_res.status_code == 200, exec_res.text
    exec_data = exec_res.json()
    assert exec_data["status"] == "COMPLETED"
    assert exec_data["anonymized"] is True
    assert exec_data["files_deleted_count"] >= 1

    # Verify physical file deleted from storage disk
    assert not temp_file.exists()

    # Verify database scrubbing
    await db_session.refresh(candidate)
    assert candidate.full_name == "[DELETED]"
    assert candidate.email is None
    assert candidate.phone is None
    assert candidate.location == "[DELETED]"
    assert candidate.is_anonymized is True
    assert candidate.deletion_status == "COMPLETED"
    assert candidate.consent_status == "WITHDRAWN"

    await db_session.refresh(resume)
    assert resume.raw_text is None
    assert resume.normalized_text is None

    # 6. Idempotency test: Re-executing deletion does not crash
    re_exec = await client.post(
        f"/api/v1/deletion-requests/{request_id}/execute",
        headers=dh_headers,
    )
    assert re_exec.status_code == 200
    assert re_exec.json()["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_deletion_cross_organization_isolation(client: AsyncClient, db_session: AsyncSession):
    recruiter_a, org_a = await seed_user_with_org(
        db_session, email="rec_a_del_iso@staffing.com", password="Password123!", role="recruiter", org_name="Org A Deletion Iso"
    )
    headers_a = auth_headers(recruiter_a.id, "recruiter", org_a.id)

    recruiter_b, org_b = await seed_user_with_org(
        db_session, email="rec_b_del_iso@staffing.com", password="Password123!", role="recruiter", org_name="Org B Deletion Iso"
    )
    headers_b = auth_headers(recruiter_b.id, "recruiter", org_b.id)

    cand_a = Candidate(
        id=uuid.uuid4(),
        organization_id=org_a.id,
        full_name="Target A",
    )
    db_session.add(cand_a)
    await db_session.commit()

    # Recruiter B attempts to request deletion of Candidate A -> 404
    cross_res = await client.post(
        f"/api/v1/candidates/{cand_a.id}/deletion-requests",
        headers=headers_b,
        json={"reason": "Unauthorized wipe attempt"},
    )
    assert cross_res.status_code == 404
