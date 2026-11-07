from __future__ import annotations

import pytest
from sqlalchemy import exc
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import create_test_org, create_test_user, create_membership


@pytest.mark.asyncio
async def test_user_email_uniqueness(db_session: AsyncSession):
    await create_test_user(db_session, email="unique_email@test.com")
    await db_session.commit()
    # Creating another user with same email must fail
    from app.models.user import User
    from app.core.security import hash_password
    dupe = User(email="unique_email@test.com", password_hash=hash_password("pass"))
    db_session.add(dupe)
    with pytest.raises((exc.IntegrityError, Exception)):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_org_membership_unique(db_session: AsyncSession):
    org = await create_test_org(db_session, name="UniqueMemOrg")
    user = await create_test_user(db_session, email="membunique@test.com")
    await create_membership(db_session, user.id, org.id, role="recruiter")
    await db_session.commit()

    # Same user + org should fail uniqueness
    from app.models.organization import OrganizationMembership
    dupe = OrganizationMembership(user_id=user.id, organization_id=org.id, role="recruiter")
    db_session.add(dupe)
    with pytest.raises((exc.IntegrityError, Exception)):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_user_creation(db_session: AsyncSession):
    user = await create_test_user(db_session, email="creation@test.com")
    await db_session.commit()
    assert user.id is not None
    assert user.is_active is True
    assert user.password_hash != "TestPassword123!"  # Never plaintext


@pytest.mark.asyncio
async def test_organization_membership(db_session: AsyncSession):
    org = await create_test_org(db_session, name="MembershipTestOrg")
    user = await create_test_user(db_session, email="membership@test.com")
    m = await create_membership(db_session, user.id, org.id, role="recruiter")
    await db_session.commit()
    assert m.role == "recruiter"
    assert m.organization_id == org.id
    assert m.user_id == user.id


@pytest.mark.asyncio
async def test_password_never_stored_plaintext(db_session: AsyncSession):
    user = await create_test_user(db_session, email="hashcheck@test.com", password="PlainPass!")
    await db_session.commit()
    assert user.password_hash != "PlainPass!"
    assert len(user.password_hash) > 20  # Hashed value is longer
