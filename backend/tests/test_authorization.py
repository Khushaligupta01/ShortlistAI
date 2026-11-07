from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import seed_user_with_org


async def _login(client: AsyncClient, email: str, password: str) -> str:
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_recruiter_can_access_requisitions(
    client: AsyncClient, db_session: AsyncSession
):
    await seed_user_with_org(
        db_session,
        email="recruiter_rbac@example.com",
        password="RecruiterPass!",
        role="recruiter",
        org_name="RBACOrg1",
    )
    token = await _login(client, "recruiter_rbac@example.com", "RecruiterPass!")
    resp = await client.get(
        "/api/v1/requisitions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_client_hm_cannot_access_requisitions(
    client: AsyncClient, db_session: AsyncSession
):
    await seed_user_with_org(
        db_session,
        email="clienthm_rbac@example.com",
        password="ClientPass!",
        role="client_hiring_manager",
        org_name="ClientOrg1",
        org_type="client_company",
    )
    token = await _login(client, "clienthm_rbac@example.com", "ClientPass!")
    resp = await client.get(
        "/api/v1/requisitions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delivery_head_can_access_requisitions(
    client: AsyncClient, db_session: AsyncSession
):
    await seed_user_with_org(
        db_session,
        email="delivery_rbac@example.com",
        password="DeliveryPass!",
        role="delivery_head",
        org_name="DeliveryOrg1",
    )
    token = await _login(client, "delivery_rbac@example.com", "DeliveryPass!")
    resp = await client.get(
        "/api/v1/requisitions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_unauthenticated_cannot_access_protected(client: AsyncClient):
    resp = await client.get("/api/v1/requisitions")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_cross_org_requisition_returns_404(
    client: AsyncClient, db_session: AsyncSession
):
    """User from org A cannot see org B's requisitions."""
    from app.models.requisition import Requisition

    user_a, org_a = await seed_user_with_org(
        db_session,
        email="user_a_iso@example.com",
        password="UserAPass!",
        role="recruiter",
        org_name="OrgA_Isolation",
    )
    _, org_b = await seed_user_with_org(
        db_session,
        email="user_b_iso@example.com",
        password="UserBPass!",
        role="recruiter",
        org_name="OrgB_Isolation",
    )
    # Create a requisition in org B
    req_b = Requisition(
        organization_id=org_b.id,
        created_by=user_a.id,
        title="Org B Job",
        job_description="JD for org B",
        status="active",
    )
    db_session.add(req_b)
    await db_session.commit()

    token_a = await _login(client, "user_a_iso@example.com", "UserAPass!")

    # User A trying to read org B's requisition should get 404
    resp = await client.get(
        f"/api/v1/requisitions/{req_b.id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 404
