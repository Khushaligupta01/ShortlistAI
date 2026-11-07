from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.asyncio
async def test_readiness(client: AsyncClient):
    response = await client.get("/api/v1/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"


@pytest.mark.asyncio
async def test_security_headers(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert "x-frame-options" in response.headers
    assert response.headers["x-frame-options"] == "DENY"
    assert "x-content-type-options" in response.headers
    assert "referrer-policy" in response.headers
    assert "content-security-policy" in response.headers
    assert "x-trace-id" in response.headers
