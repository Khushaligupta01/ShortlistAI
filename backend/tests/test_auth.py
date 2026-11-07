from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import create_test_user, seed_user_with_org


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, db_session: AsyncSession):
    user, org = await seed_user_with_org(
        db_session,
        email="recruiter_login@example.com",
        password="ValidPass123!",
        role="recruiter",
        org_name="LoginTestOrg",
    )
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "recruiter_login@example.com", "password": "ValidPass123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, db_session: AsyncSession):
    await seed_user_with_org(
        db_session,
        email="wrongpass@example.com",
        password="CorrectPassword!",
        role="recruiter",
        org_name="WrongPassOrg",
    )
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "wrongpass@example.com", "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    body = response.json()
    msg = body.get("detail") or body.get("message", "")
    assert "Invalid email or password" in msg


@pytest.mark.asyncio
async def test_login_unknown_email(client: AsyncClient, db_session: AsyncSession):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@nowhere.com", "password": "AnyPassword!"},
    )
    assert response.status_code == 401
    # Must return same message as wrong password — non-disclosure
    body = response.json()
    msg = body.get("detail") or body.get("message", "")
    assert "Invalid email or password" in msg


@pytest.mark.asyncio
async def test_login_inactive_account(client: AsyncClient, db_session: AsyncSession):
    from app.models.organization import Organization
    org = Organization(name="InactiveOrg", org_type="staffing_firm")
    db_session.add(org)
    await db_session.flush()
    user = await create_test_user(
        db_session,
        email="inactive@example.com",
        password="SomePass123!",
        is_active=False,
    )
    await db_session.commit()

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "inactive@example.com", "password": "SomePass123!"},
    )
    assert response.status_code == 401
    body = response.json()
    msg = body.get("detail") or body.get("message", "")
    assert "Invalid email or password" in msg


@pytest.mark.asyncio
async def test_me_with_valid_token(client: AsyncClient, db_session: AsyncSession):
    await seed_user_with_org(
        db_session,
        email="me_test@example.com",
        password="MePass123!",
        role="recruiter",
        org_name="MeTestOrg",
    )
    # Login first
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "me_test@example.com", "password": "MePass123!"},
    )
    token = login_resp.json()["access_token"]

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me_test@example.com"
    assert data["role"] == "recruiter"


@pytest.mark.asyncio
async def test_me_without_token(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, db_session: AsyncSession):
    await seed_user_with_org(
        db_session,
        email="refresh_test@example.com",
        password="RefreshPass123!",
        role="recruiter",
        org_name="RefreshOrg",
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "refresh_test@example.com", "password": "RefreshPass123!"},
    )
    refresh_token = login_resp.json()["refresh_token"]

    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_resp.status_code == 200
    new_data = refresh_resp.json()
    assert "access_token" in new_data
    assert "refresh_token" in new_data
    # Old refresh token should now be revoked (single-use)
    reuse_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert reuse_resp.status_code == 401


@pytest.mark.asyncio
async def test_logout(client: AsyncClient, db_session: AsyncSession):
    await seed_user_with_org(
        db_session,
        email="logout_test@example.com",
        password="LogoutPass123!",
        role="recruiter",
        org_name="LogoutOrg",
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "logout_test@example.com", "password": "LogoutPass123!"},
    )
    tokens = login_resp.json()
    refresh_token = tokens["refresh_token"]

    logout_resp = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert logout_resp.status_code == 204

    # After logout, refresh token is revoked
    reuse_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert reuse_resp.status_code == 401
