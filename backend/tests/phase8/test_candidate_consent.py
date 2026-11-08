from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.audit import ConsentRecord
from app.models.candidate import Candidate
from app.models.organization import Organization
from tests.conftest import auth_headers, create_test_org, seed_user_with_org


@pytest.mark.asyncio
async def test_consent_request_lifecycle(client: AsyncClient, db_session: AsyncSession):
    # 1. Setup staffing organization and recruiter
    recruiter, org = await seed_user_with_org(
        db_session, email="recruiter_consent@staffing.com", password="Password123!", role="recruiter", org_name="Apex Consent Org"
    )
    recruiter_headers = auth_headers(recruiter.id, "recruiter", org.id)

    # 2. Create Candidate
    candidate = Candidate(
        id=uuid.uuid4(),
        organization_id=org.id,
        full_name="Elena Rostova",
        email="elena.rostova@example.com",
        phone="+15550198888",
        location="Austin, TX",
        total_experience_years=7.5,
        consent_status="GRANTED",
    )
    db_session.add(candidate)
    await db_session.commit()

    # 3. Recruiter creates consent request
    create_res = await client.post(
        f"/api/v1/candidates/{candidate.id}/consent-requests",
        headers=recruiter_headers,
        json={
            "purpose": "resume_screening_and_shortlisting",
            "collection_method": "PUBLIC_LINK",
        },
    )
    assert create_res.status_code == 201, create_res.text
    create_data = create_res.json()
    assert create_data["status"] == "PENDING"
    raw_token = create_data["token"]
    assert raw_token is not None
    assert "public/consent/" in create_data["consent_url"]

    # Verify token is hashed at rest in DB
    expected_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    db_rec_res = await db_session.execute(
        select(ConsentRecord).where(ConsentRecord.token_hash == expected_hash)
    )
    db_record = db_rec_res.scalar_one_or_none()
    assert db_record is not None
    assert db_record.token_hash == expected_hash
    # Candidate status should be PENDING
    await db_session.refresh(candidate)
    assert candidate.consent_status == "PENDING"

    # 4. Candidate accesses public link
    pub_res = await client.get(f"/api/v1/public/consent/{raw_token}")
    assert pub_res.status_code == 200, pub_res.text
    pub_data = pub_res.json()
    assert pub_data["is_valid"] is True
    assert "CND-" in pub_data["candidate_reference"]
    assert pub_data["organization_name"] == org.name

    # 5. Candidate grants consent
    decision_res = await client.post(
        f"/api/v1/public/consent/{raw_token}/decision",
        json={
            "decision": "GRANTED",
            "reason": "Authorized for Austin tech roles",
        },
    )
    assert decision_res.status_code == 200, decision_res.text
    assert decision_res.json()["status"] == "GRANTED"

    # Verify candidate consent status updated
    await db_session.refresh(candidate)
    assert candidate.consent_status == "GRANTED"

    # 6. Verify single-use token: token reuse must be rejected
    reuse_res = await client.post(
        f"/api/v1/public/consent/{raw_token}/decision",
        json={"decision": "DECLINED"},
    )
    assert reuse_res.status_code == 400
    err_text = (reuse_res.json().get("message") or reuse_res.json().get("detail") or "").lower()
    assert "already been used" in err_text

    # 7. Recruiter checks consent history
    history_res = await client.get(
        f"/api/v1/candidates/{candidate.id}/consent",
        headers=recruiter_headers,
    )
    assert history_res.status_code == 200
    history_items = history_res.json()
    assert len(history_items) >= 1
    assert history_items[0]["status"] == "GRANTED"

    # 8. Recruiter withdraws consent
    withdraw_res = await client.post(
        f"/api/v1/candidates/{candidate.id}/consent/withdraw",
        headers=recruiter_headers,
        json={"reason": "Candidate requested withdrawal via email."},
    )
    assert withdraw_res.status_code == 200
    assert withdraw_res.json()["status"] == "WITHDRAWN"

    await db_session.refresh(candidate)
    assert candidate.consent_status == "WITHDRAWN"


@pytest.mark.asyncio
async def test_consent_token_expiry(client: AsyncClient, db_session: AsyncSession):
    # Setup
    recruiter, org = await seed_user_with_org(
        db_session, email="recruiter_exp@staffing.com", password="Password123!", role="recruiter", org_name="Expiry Test Org"
    )
    recruiter_headers = auth_headers(recruiter.id, "recruiter", org.id)

    candidate = Candidate(
        id=uuid.uuid4(),
        organization_id=org.id,
        full_name="Marcus Vance",
        email="marcus.vance@example.com",
    )
    db_session.add(candidate)
    await db_session.commit()

    # Create consent request
    res = await client.post(
        f"/api/v1/candidates/{candidate.id}/consent-requests",
        headers=recruiter_headers,
        json={"purpose": "demo_purpose"},
    )
    raw_token = res.json()["token"]
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    # Manually backdate token_expires_at to simulate expiry
    db_rec = (await db_session.execute(
        select(ConsentRecord).where(ConsentRecord.token_hash == token_hash)
    )).scalar_one()
    db_rec.token_expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    await db_session.commit()

    # Candidate attempts to submit expired token
    dec_res = await client.post(
        f"/api/v1/public/consent/{raw_token}/decision",
        json={"decision": "GRANTED"},
    )
    assert dec_res.status_code == 400
    err_text = (dec_res.json().get("message") or dec_res.json().get("detail") or "").lower()
    assert "expired" in err_text


@pytest.mark.asyncio
async def test_consent_cross_organization_isolation(client: AsyncClient, db_session: AsyncSession):
    # Org A
    recruiter_a, org_a = await seed_user_with_org(
        db_session, email="rec_a_iso@staffing.com", password="Password123!", role="recruiter", org_name="Org A Isolation"
    )
    headers_a = auth_headers(recruiter_a.id, "recruiter", org_a.id)

    # Org B
    recruiter_b, org_b = await seed_user_with_org(
        db_session, email="rec_b_iso@staffing.com", password="Password123!", role="recruiter", org_name="Org B Isolation"
    )
    headers_b = auth_headers(recruiter_b.id, "recruiter", org_b.id)

    # Candidate belongs to Org A
    cand_a = Candidate(
        id=uuid.uuid4(),
        organization_id=org_a.id,
        full_name="Private Candidate A",
        email="cand_a@example.com",
    )
    db_session.add(cand_a)
    await db_session.commit()

    # Recruiter B attempts to create consent request for Candidate A -> 404
    cross_res = await client.post(
        f"/api/v1/candidates/{cand_a.id}/consent-requests",
        headers=headers_b,
        json={"purpose": "illicit_purpose"},
    )
    assert cross_res.status_code == 404
