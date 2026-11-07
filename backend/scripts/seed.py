"""
Idempotent development seed script.

Run from the backend/ directory:
    python scripts/seed.py

Environment variables used:
    DATABASE_URL             (from .env)
    SEED_RECRUITER_PASSWORD  default: Recruiter@Demo2024!
    SEED_CLIENT_PASSWORD     default: Client@Demo2024!
    SEED_DELIVERY_PASSWORD   default: Delivery@Demo2024!
"""
from __future__ import annotations

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User
from app.models.organization import Organization, OrganizationMembership
from app.models.requisition import Requisition
from app.models.candidate import Candidate
from app.db.base import Base

engine = create_async_engine(settings.DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def get_or_create_org(session: AsyncSession, name: str, org_type: str) -> Organization:
    result = await session.execute(select(Organization).where(Organization.name == name))
    org = result.scalar_one_or_none()
    if not org:
        org = Organization(name=name, org_type=org_type)
        session.add(org)
        await session.flush()
        print(f"  Created org: {name}")
    else:
        print(f"  Org exists: {name}")
    return org


async def get_or_create_user(
    session: AsyncSession,
    email: str,
    password: str,
    display_name: str,
) -> User:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            email=email,
            password_hash=hash_password(password),
            display_name=display_name,
            is_active=True,
            is_verified=True,
        )
        session.add(user)
        await session.flush()
        print(f"  Created user: {email}")
    else:
        print(f"  User exists: {email}")
    return user


async def ensure_membership(
    session: AsyncSession, user_id, org_id, role: str
) -> None:
    result = await session.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.organization_id == org_id,
        )
    )
    if not result.scalar_one_or_none():
        session.add(OrganizationMembership(user_id=user_id, organization_id=org_id, role=role))
        await session.flush()
        print(f"  Added membership: {role}")


async def seed() -> None:
    print("=== ShortlistAI Seed Script ===")
    print(f"DATABASE_URL: {settings.DATABASE_URL[:30]}...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        # Organizations
        staffing_org = await get_or_create_org(session, "TechRecruit Ltd", "staffing_firm")
        client_org = await get_or_create_org(session, "Acme Technologies", "client_company")

        # Users
        recruiter = await get_or_create_user(
            session,
            email="recruiter@techrecruit.com",
            password=settings.SEED_RECRUITER_PASSWORD,
            display_name="Alice Recruiter",
        )
        client_hm = await get_or_create_user(
            session,
            email="client@acme.com",
            password=settings.SEED_CLIENT_PASSWORD,
            display_name="Bob Client",
        )
        delivery_head = await get_or_create_user(
            session,
            email="head@techrecruit.com",
            password=settings.SEED_DELIVERY_PASSWORD,
            display_name="Carol Head",
        )

        # Memberships
        await ensure_membership(session, recruiter.id, staffing_org.id, "recruiter")
        await ensure_membership(session, client_hm.id, client_org.id, "client_hiring_manager")
        await ensure_membership(session, delivery_head.id, staffing_org.id, "delivery_head")

        # Requisition
        result = await session.execute(
            select(Requisition).where(
                Requisition.title == "Senior Java Developer",
                Requisition.organization_id == staffing_org.id,
            )
        )
        if not result.scalar_one_or_none():
            req = Requisition(
                organization_id=staffing_org.id,
                created_by=recruiter.id,
                title="Senior Java Developer",
                job_description=(
                    "We are looking for a Senior Java Developer with 5+ years of experience.\n"
                    "Must have: Java, Spring Boot, PostgreSQL\n"
                    "Nice to have: Kubernetes, AWS\n"
                    "Location: London or Remote\n"
                    "Notice period: Maximum 30 days"
                ),
                status="active",
            )
            session.add(req)
            print("  Created requisition: Senior Java Developer")
        else:
            print("  Requisition exists: Senior Java Developer")

        # Synthetic candidates
        candidate_data = [
            ("Alice Smith", "alice.smith@example.com", "+44 7700 900001", "London"),
            ("Bob Jones", "bob.jones@example.com", "+44 7700 900002", "Manchester"),
            ("Carol Williams", "carol.williams@example.com", "+44 7700 900003", "Remote"),
        ]
        for full_name, email, phone, location in candidate_data:
            result = await session.execute(
                select(Candidate).where(
                    Candidate.email == email,
                    Candidate.organization_id == staffing_org.id,
                )
            )
            if not result.scalar_one_or_none():
                session.add(
                    Candidate(
                        organization_id=staffing_org.id,
                        full_name=full_name,
                        email=email,
                        phone=phone,
                        location=location,
                    )
                )
                print(f"  Created candidate: {full_name}")
            else:
                print(f"  Candidate exists: {full_name}")

        await session.commit()

    print("\n=== Seed complete ===")
    print("Demo accounts:")
    print(f"  Recruiter:      recruiter@techrecruit.com  / {settings.SEED_RECRUITER_PASSWORD}")
    print(f"  Client HM:      client@acme.com            / {settings.SEED_CLIENT_PASSWORD}")
    print(f"  Delivery Head:  head@techrecruit.com       / {settings.SEED_DELIVERY_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(seed())
