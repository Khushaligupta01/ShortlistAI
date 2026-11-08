from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models as _all_models  # noqa: F401 - Register all models with Base.metadata
from app.db.base import Base
from app.db.session import get_db
from app.main import app

# ── Test database (SQLite in-memory via aiosqlite) ──────────────────────────
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_shortlistai.db"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)

from app.services.evaluation_service import evaluation_service
evaluation_service.session_factory = TestSessionLocal


@pytest_asyncio.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP client with overridden DB dependency."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.clear()


# ── Seed helpers ─────────────────────────────────────────────────────────────

async def create_test_org(
    db: AsyncSession,
    name: str = "Test Staffing",
    org_type: str = "staffing_firm",
):
    from app.models.organization import Organization
    org = Organization(name=name, org_type=org_type)
    db.add(org)
    await db.flush()
    await db.refresh(org)
    return org


async def create_test_user(
    db: AsyncSession,
    email: str = "test@example.com",
    password: str = "TestPassword123!",
    display_name: str = "Test User",
    is_active: bool = True,
):
    from app.core.security import hash_password
    from app.models.user import User
    user = User(
        email=email,
        password_hash=hash_password(password),
        display_name=display_name,
        is_active=is_active,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def create_membership(
    db: AsyncSession,
    user_id: uuid.UUID,
    org_id: uuid.UUID,
    role: str = "recruiter",
):
    from app.models.organization import OrganizationMembership
    m = OrganizationMembership(user_id=user_id, organization_id=org_id, role=role)
    db.add(m)
    await db.flush()
    return m


async def seed_user_with_org(
    db: AsyncSession,
    email: str,
    password: str,
    role: str,
    org_name: str = "Test Org",
    org_type: str = "staffing_firm",
):
    org = await create_test_org(db, name=org_name, org_type=org_type)
    user = await create_test_user(db, email=email, password=password)
    await create_membership(db, user.id, org.id, role=role)
    await db.commit()
    return user, org


def auth_headers(user_id: uuid.UUID, role: str, org_id: uuid.UUID) -> dict[str, str]:
    from app.core.security import create_access_token
    token = create_access_token({"sub": str(user_id), "role": role, "org_id": str(org_id)})
    return {"Authorization": f"Bearer {token}"}
    return user, org
