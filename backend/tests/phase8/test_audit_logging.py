from __future__ import annotations

import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.audit import AuditLog
from app.services.audit_service import log_event, sanitize_payload
from tests.conftest import auth_headers, create_test_org, seed_user_with_org


def test_sanitize_payload():
    raw_payload = {
        "candidate_id": "123",
        "action": "login",
        "password": "SuperSecretPassword123!",
        "access_token": "eyJhbGciOi...",
        "api_key": "sk-1234567890",
        "raw_text": "Full private resume text",
        "nested": {
            "secret": "confidential_key",
            "safe_field": "visible_info",
        },
    }
    clean = sanitize_payload(raw_payload)
    assert clean["candidate_id"] == "123"
    assert clean["action"] == "login"
    assert clean["password"] == "[REDACTED]"
    assert clean["access_token"] == "[REDACTED]"
    assert clean["api_key"] == "[REDACTED]"
    assert clean["raw_text"] == "[REDACTED]"
    assert clean["nested"]["secret"] == "[REDACTED]"
    assert clean["nested"]["safe_field"] == "visible_info"


@pytest.mark.asyncio
async def test_audit_logging_and_querying(client: AsyncClient, db_session: AsyncSession):
    # Setup Recruiter & Org
    recruiter, org = await seed_user_with_org(
        db_session, email="rec_audit@staffing.com", password="Password123!", role="recruiter", org_name="Apex Audit Org"
    )
    recruiter_headers = auth_headers(recruiter.id, "recruiter", org.id)

    # Log critical events using audit service
    cand_id = uuid.uuid4()
    await log_event(
        db=db_session,
        organization_id=org.id,
        actor_user_id=recruiter.id,
        event_type="TEST_SECURITY_EVENT",
        resource_type="candidate",
        resource_id=cand_id,
        payload={
            "action": "audit_verification",
            "token": "sensitive_token_to_redact",
        },
        commit=True,
    )

    # Query audit logs via API
    list_res = await client.get(
        "/api/v1/audit-events",
        headers=recruiter_headers,
        params={"event_type": "TEST_SECURITY_EVENT"},
    )
    assert list_res.status_code == 200, list_res.text
    list_data = list_res.json()
    assert list_data["total"] >= 1
    event = list_data["items"][0]
    assert event["event_type"] == "TEST_SECURITY_EVENT"
    assert event["resource_type"] == "candidate"
    assert event["resource_id"] == str(cand_id)
    assert event["payload_json"]["action"] == "audit_verification"
    assert event["payload_json"]["token"] == "[REDACTED]"

    # Get single event
    get_res = await client.get(
        f"/api/v1/audit-events/{event['id']}",
        headers=recruiter_headers,
    )
    assert get_res.status_code == 200
    assert get_res.json()["id"] == event["id"]


@pytest.mark.asyncio
async def test_audit_cross_organization_isolation(client: AsyncClient, db_session: AsyncSession):
    recruiter_a, org_a = await seed_user_with_org(
        db_session, email="rec_a_aud_iso@staffing.com", password="Password123!", role="recruiter", org_name="Org A Aud Iso"
    )
    headers_a = auth_headers(recruiter_a.id, "recruiter", org_a.id)

    recruiter_b, org_b = await seed_user_with_org(
        db_session, email="rec_b_aud_iso@staffing.com", password="Password123!", role="recruiter", org_name="Org B Aud Iso"
    )
    headers_b = auth_headers(recruiter_b.id, "recruiter", org_b.id)

    # Log event in Org A
    event_a = await log_event(
        db=db_session,
        organization_id=org_a.id,
        actor_user_id=recruiter_a.id,
        event_type="ORG_A_PRIVATE_EVENT",
        resource_type="system",
        commit=True,
    )

    # Recruiter B attempts to read event A -> 404
    cross_res = await client.get(
        f"/api/v1/audit-events/{event_a.id}",
        headers=headers_b,
    )
    assert cross_res.status_code == 404
