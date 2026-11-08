from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.organization import Organization, OrganizationMembership
from app.models.user import User
from tests.conftest import auth_headers


@pytest.mark.asyncio
async def test_workflow_a_recruiter_onboarding_and_auth(client: AsyncClient, db_session: AsyncSession):
    """
    Workflow A:
    1. Provision recruiter account in database.
    2. Authenticate via POST /api/v1/auth/login.
    3. Verify authenticated identity via GET /api/v1/auth/me.
    4. Access recruiter dashboard metrics via GET /api/v1/dashboard/metrics.
    5. Verify role-based permissions (can access requisitions, blocked from client portal).
    6. Logout via POST /api/v1/auth/logout.
    7. Verify protected resources reject unauthenticated requests.
    """
    # 1. Provision organization and recruiter user
    org_id = uuid.uuid4()
    org = Organization(id=org_id, name="TalentBridge Global", org_type="staffing_firm")
    db_session.add(org)

    user_id = uuid.uuid4()
    email = "recruiter.john@talentbridge.com"
    raw_password = "SecureRecruiterPass123!"
    recruiter = User(
        id=user_id,
        email=email,
        password_hash=hash_password(raw_password),
        display_name="John Recruiter",
        is_active=True,
        is_verified=True,
    )
    db_session.add(recruiter)

    membership = OrganizationMembership(
        id=uuid.uuid4(),
        user_id=user_id,
        organization_id=org_id,
        role="recruiter",
    )
    db_session.add(membership)
    await db_session.commit()

    # 2. Login
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": raw_password},
    )
    assert login_res.status_code == 200, login_res.text
    login_data = login_res.json()
    assert "access_token" in login_data
    access_token = login_data["access_token"]
    assert login_data["token_type"].lower() == "bearer"

    headers = {"Authorization": f"Bearer {access_token}"}

    # 3. Verify /auth/me
    me_res = await client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == email
    assert me_data["role"] == "recruiter"
    assert me_data["organization_id"] == str(org_id)

    # 4. Open recruiter dashboard metrics
    dash_res = await client.get("/api/v1/recruiter/metrics", headers=headers)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert "active_requisitions" in dash_data
    assert "total_candidates" in dash_data

    # 5. Role-specific navigation:
    # Recruiter can access requisitions
    req_res = await client.get("/api/v1/requisitions", headers=headers)
    assert req_res.status_code == 200

    # Recruiter cannot access client-only dashboard
    client_res = await client.get("/api/v1/client/dashboard", headers=headers)
    assert client_res.status_code == 403

    # 6. Logout
    logout_res = await client.post(
        "/api/v1/auth/logout",
        headers=headers,
        json={"refresh_token": login_data["refresh_token"]},
    )
    assert logout_res.status_code in (200, 204)

    # 7. Verify protected endpoints reject unauthenticated access
    unauth_res = await client.get("/api/v1/recruiter/metrics")
    assert unauth_res.status_code == 401
