"""
Idempotent development and demo seed script for ShortlistAI.

Populates a comprehensive demo dataset:
- 2 Staffing firms & 2 Client companies
- Multiple roles (Recruiters, Delivery Heads, Client Hiring Managers)
- Active Requisitions with Approved Scorecards & criteria
- 10 Diverse Candidates across high/medium/low match tiers
- Parsed resumes, work history, skills, notes, evaluations
- Recruiter review decisions (SHORTLIST, REJECT, HOLD, UNREVIEWED)
- Client portal submissions in multiple pipeline stages (SUBMITTED, CLIENT_SHORTLISTED, INTERVIEW_REQUESTED, CLIENT_REJECTED)
- Client interview requests and inquiries
- Candidate consent records & audit logs

Run from backend/:
    python scripts/seed.py
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.models.audit import AuditLog, ConsentRecord
from app.models.candidate import Candidate, CandidateEducation, CandidateEmployment, CandidateSkill
from app.models.candidate_note import CandidateNote
from app.models.evaluation import Evaluation, EvaluationEvidence, RecruiterReview
from app.models.organization import Organization, OrganizationMembership
from app.models.requisition import Requisition
from app.models.resume import Resume, UploadBatch
from app.models.scorecard import Scorecard, ScorecardCriterion
from app.models.submission import ClientRequest, PipelineRecord, Submission
from app.models.user import User

engine = create_async_engine(settings.DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def get_or_create_org(session: AsyncSession, name: str, org_type: str) -> Organization:
    res = await session.execute(select(Organization).where(Organization.name == name))
    org = res.scalars().first()
    if not org:
        org = Organization(name=name, org_type=org_type)
        session.add(org)
        await session.flush()
        print(f"  [+] Created org: {name} ({org_type})")
    return org


async def get_or_create_user(session: AsyncSession, email: str, password: str, display_name: str) -> User:
    res = await session.execute(select(User).where(User.email == email))
    user = res.scalars().first()
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
        print(f"  [+] Created user: {email} ({display_name})")
    return user


async def ensure_membership(session: AsyncSession, user_id: uuid.UUID, org_id: uuid.UUID, role: str) -> None:
    res = await session.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.organization_id == org_id,
        )
    )
    if not res.scalars().first():
        session.add(OrganizationMembership(user_id=user_id, organization_id=org_id, role=role))
        await session.flush()
        print(f"  [+] Added membership: user {user_id} -> org {org_id} as {role}")


async def seed() -> None:
    print("==================================================")
    print("         ShortlistAI Comprehensive Demo Seed       ")
    print("==================================================")
    print(f"Target DB: {settings.DATABASE_URL[:40]}...\n")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        # 1. Organizations
        print("[1/7] Seeding Organizations...")
        staffing_org1 = await get_or_create_org(session, "TechRecruit Global", "staffing_firm")
        staffing_org2 = await get_or_create_org(session, "Apex Talent Partners", "staffing_firm")
        client_org1 = await get_or_create_org(session, "Acme Cloud Systems", "client_company")
        client_org2 = await get_or_create_org(session, "Starlight Health Tech", "client_company")

        # 2. Users
        print("\n[2/7] Seeding Users & Memberships...")
        recruiter1 = await get_or_create_user(
            session, "recruiter@techrecruit.com", settings.SEED_RECRUITER_PASSWORD, "Alice Recruiter"
        )
        dh1 = await get_or_create_user(
            session, "head@techrecruit.com", settings.SEED_DELIVERY_PASSWORD, "Carol Delivery Head"
        )
        client_hm1 = await get_or_create_user(
            session, "client@acme.com", settings.SEED_CLIENT_PASSWORD, "Bob Client Manager"
        )
        client_hm2 = await get_or_create_user(
            session, "client@starlight.com", settings.SEED_CLIENT_PASSWORD, "Dr. Sarah Health HM"
        )
        recruiter2 = await get_or_create_user(
            session, "recruiter2@apextalent.com", settings.SEED_RECRUITER_PASSWORD, "Dave Recruiter"
        )

        await ensure_membership(session, recruiter1.id, staffing_org1.id, "recruiter")
        await ensure_membership(session, dh1.id, staffing_org1.id, "delivery_head")
        await ensure_membership(session, client_hm1.id, client_org1.id, "client_hiring_manager")
        await ensure_membership(session, client_hm2.id, client_org2.id, "client_hiring_manager")
        await ensure_membership(session, recruiter2.id, staffing_org2.id, "recruiter")

        # 3. Requisitions
        print("\n[3/7] Seeding Active Requisitions with Scorecards...")
        reqs_def = [
            {
                "title": "Senior Java Backend Architect",
                "client_org": client_org1,
                "staffing_org": staffing_org1,
                "recruiter": recruiter1,
                "location": "San Francisco, CA / Hybrid",
                "department": "Core Infrastructure",
                "jd": (
                    "Acme Cloud Systems seeks a Senior Java Backend Architect.\n"
                    "Requirements:\n"
                    "- 7+ years of core Java and enterprise system design.\n"
                    "- 4+ years of Spring Boot, Kafka, and microservice architecture.\n"
                    "- Experience with PostgreSQL and high-throughput streaming systems.\n"
                    "- Location: San Francisco Bay Area or Hybrid.\n"
                    "- Notice period: under 45 days."
                ),
                "criteria": [
                    ("7+ years Java Experience", "experience", 25, True),
                    ("Spring Boot & Microservices", "must_have_skills", 35, True),
                    ("Distributed Messaging (Kafka)", "nice_to_have_skills", 20, False),
                    ("Location & Notice Period", "location", 20, False),
                ],
            },
            {
                "title": "Lead Full Stack Python Engineer",
                "client_org": client_org1,
                "staffing_org": staffing_org1,
                "recruiter": recruiter1,
                "location": "Remote USA",
                "department": "Platform Services",
                "jd": (
                    "Looking for a Lead Python Full Stack Engineer with FastAPI, React, and AWS.\n"
                    "Requirements:\n"
                    "- 6+ years professional software development.\n"
                    "- Python, FastAPI, SQLAlchemy, PostgreSQL.\n"
                    "- Modern React with TypeScript.\n"
                    "- Notice period: Immediate or up to 30 days."
                ),
                "criteria": [
                    ("6+ years Python Development", "experience", 30, True),
                    ("FastAPI & React TypeScript", "must_have_skills", 40, True),
                    ("AWS Cloud & Docker", "nice_to_have_skills", 15, False),
                    ("Immediate / 30d Notice", "notice_period", 15, False),
                ],
            },
            {
                "title": "Staff Privacy & Security Engineer",
                "client_org": client_org2,
                "staffing_org": staffing_org1,
                "recruiter": recruiter1,
                "location": "Boston, MA / Remote",
                "department": "Information Security",
                "jd": (
                    "Starlight Health Tech is seeking a Staff Privacy and Compliance Engineer.\n"
                    "Requirements:\n"
                    "- 5+ years handling HIPAA, GDPR, and health data governance.\n"
                    "- Experience building access control, audit trails, and data deletion workflows.\n"
                    "- Strong Python or Go security tooling."
                ),
                "criteria": [
                    ("5+ years Privacy Engineering", "experience", 35, True),
                    ("HIPAA & Health Data Governance", "must_have_skills", 35, True),
                    ("Audit Logging & Deletion Systems", "must_have_skills", 20, True),
                    ("Security Tooling (Python/Go)", "nice_to_have_skills", 10, False),
                ],
            },
        ]

        created_reqs = []
        for rdef in reqs_def:
            res = await session.execute(
                select(Requisition).where(
                    Requisition.title == rdef["title"],
                    Requisition.organization_id == rdef["staffing_org"].id,
                )
            )
            req = res.scalars().first()
            if not req:
                req = Requisition(
                    organization_id=rdef["staffing_org"].id,
                    client_organization_id=rdef["client_org"].id,
                    created_by=rdef["recruiter"].id,
                    title=rdef["title"],
                    location=rdef["location"],
                    job_description=rdef["jd"],
                    status="active",
                )
                session.add(req)
                await session.flush()
                print(f"  [+] Created Requisition: {req.title}")
            created_reqs.append(req)

            # Check or create approved scorecard
            sc_res = await session.execute(
                select(Scorecard).where(Scorecard.requisition_id == req.id)
            )
            sc = sc_res.scalars().first()
            if not sc:
                sc = Scorecard(
                    requisition_id=req.id,
                    version_number=1,
                    status="approved",
                    scoring_config={
                        "experience": 30,
                        "must_have_skills": 40,
                        "nice_to_have_skills": 15,
                        "location": 10,
                        "notice_period": 5,
                    },
                )
                session.add(sc)
                await session.flush()

                for c_name, c_type, c_weight, c_mand in rdef["criteria"]:
                    crit = ScorecardCriterion(
                        scorecard_id=sc.id,
                        criterion_name=c_name,
                        criterion_type=c_type,
                        label=c_name,
                        weight=c_weight,
                        is_mandatory=c_mand,
                    )
                    session.add(crit)
                await session.flush()
                print(f"      [+] Attached Approved Scorecard v1 with {len(rdef['criteria'])} criteria")

        # 4. Candidates
        print("\n[4/7] Seeding Diverse Synthetic Candidates...")
        candidate_specs = [
            # High matches
            ("Marcus Vance", "marcus.vance@demo.shortlistai.com", "+1-415-555-0101", "San Francisco, CA", 9.5, 15, "GRANTED", 92.5, "SHORTLIST", "HIGH"),
            ("Elena Rostova", "elena.rostova@demo.shortlistai.com", "+1-415-555-0102", "San Jose, CA", 8.0, 30, "GRANTED", 89.0, "SHORTLIST", "HIGH"),
            ("Priya Patel", "priya.patel@demo.shortlistai.com", "+1-206-555-0103", "Seattle, WA", 7.0, 30, "GRANTED", 86.5, "SHORTLIST", "HIGH"),
            # Medium matches
            ("Devon Miller", "devon.miller@demo.shortlistai.com", "+1-312-555-0104", "Chicago, IL", 6.0, 45, "GRANTED", 74.0, "HOLD", "MEDIUM"),
            ("Chloe Bennett", "chloe.bennett@demo.shortlistai.com", "+1-617-555-0105", "Boston, MA", 5.5, 60, "GRANTED", 71.5, "HOLD", "MEDIUM"),
            ("Tariq Al-Mansoor", "tariq.almansoor@demo.shortlistai.com", "+1-512-555-0106", "Austin, TX", 5.0, 30, "GRANTED", 68.0, "UNREVIEWED", "MEDIUM"),
            # Low matches / Under-qualified controls
            ("Samir Roy", "samir.roy@demo.shortlistai.com", "+1-212-555-0107", "New York, NY", 2.0, 15, "GRANTED", 44.0, "REJECT", "LOW"),
            ("Hannah Schmidt", "hannah.schmidt@demo.shortlistai.com", "+1-303-555-0108", "Denver, CO", 1.5, 90, "GRANTED", 38.5, "REJECT", "LOW"),
            # Governance / Edge Cases
            ("Lucas Silva (Withdrawn)", "lucas.silva@demo.shortlistai.com", "+1-404-555-0109", "Atlanta, GA", 6.0, 30, "WITHDRAWN", 80.0, "HOLD", "MEDIUM"),
            ("Zoe Zhang (Pending Consent)", "zoe.zhang@demo.shortlistai.com", "+1-650-555-0110", "Palo Alto, CA", 7.5, 30, "PENDING", 85.0, "UNREVIEWED", "HIGH"),
        ]

        seeded_candidates = []
        target_req = created_reqs[0]  # Senior Java Backend Architect

        # Fetch approved scorecard for target_req
        sc_res = await session.execute(
            select(Scorecard).where(Scorecard.requisition_id == target_req.id, Scorecard.status == "approved")
        )
        target_sc = sc_res.scalars().first()

        for name, email, phone, loc, exp, notice, consent, score, decision, conf in candidate_specs:
            res = await session.execute(
                select(Candidate).where(Candidate.email == email, Candidate.organization_id == staffing_org1.id)
            )
            cand = res.scalars().first()
            if not cand:
                cand = Candidate(
                    organization_id=staffing_org1.id,
                    full_name=name,
                    email=email,
                    phone=phone,
                    location=loc,
                    total_experience_years=exp,
                    notice_period_days=notice,
                    consent_status=consent,
                    parsed_profile_json={
                        "summary": f"Professional software engineer with {exp} years of specialized experience.",
                        "headline": f"Software Engineer - {loc}",
                    },
                )
                session.add(cand)
                await session.flush()

                # Resume record
                resume = Resume(
                    candidate_id=cand.id,
                    organization_id=staffing_org1.id,
                    requisition_id=target_req.id,
                    file_name=f"{name.split()[0].lower()}_cv.pdf",
                    storage_path=f"storage/resumes/{cand.id}.pdf",
                    mime_type="application/pdf",
                    file_size_bytes=45200,
                    parse_status="parsed",
                    raw_text=f"{name}. {exp} years software experience in {loc}. Contact: {email}.",
                    normalized_text=f"{name}. {exp} years software experience in {loc}. Contact: {email}.",
                )
                session.add(resume)

                # Skills
                for skill_name in ["Java", "Spring Boot", "Kafka", "PostgreSQL", "Docker", "Microservices"]:
                    session.add(CandidateSkill(candidate_id=cand.id, name=skill_name, raw_name=skill_name))

                # Employment
                session.add(
                    CandidateEmployment(
                        candidate_id=cand.id,
                        company="Global Tech Systems",
                        job_title="Lead Software Engineer",
                        start_date="2020-01-01",
                        is_current=True,
                        description="Architecting microservices and real-time distributed data pipelines.",
                    )
                )

                # Internal note
                session.add(
                    CandidateNote(
                        candidate_id=cand.id,
                        organization_id=staffing_org1.id,
                        author_id=recruiter1.id,
                        requisition_id=target_req.id,
                        content=f"Initial screen completed. Candidate demonstrates solid {exp}y engineering background. Decision: {decision}.",
                    )
                )

                # Evaluation & Review
                if target_sc:
                    ev = Evaluation(
                        candidate_id=cand.id,
                        organization_id=staffing_org1.id,
                        requisition_id=target_req.id,
                        scorecard_id=target_sc.id,
                        version_number=1,
                        scorecard_version=1,
                        is_current=True,
                        total_score=score,
                        raw_score=score,
                        normalized_score=score,
                        evaluation_status="COMPLETED",
                        confidence_level=conf,
                        score_breakdown_json={
                            "experience_score": min(score * 0.95, 100.0),
                            "skills_score": score,
                            "location_score": 90.0 if "San Francisco" in loc else 75.0,
                            "notice_score": 100.0 if notice <= 30 else 70.0,
                        },
                    )
                    session.add(ev)
                    await session.flush()

                    if decision != "UNREVIEWED":
                        rev = RecruiterReview(
                            evaluation_id=ev.id,
                            recruiter_id=recruiter1.id,
                            organization_id=staffing_org1.id,
                            decision=decision,
                            notes=f"Recruiter review finalized with status {decision}.",
                            reviewed_at=datetime.now(timezone.utc) - timedelta(days=2),
                        )
                        session.add(rev)

                print(f"  [+] Seeded candidate: {name} (Score: {score}, Review: {decision}, Consent: {consent})")
            seeded_candidates.append(cand)

        # 5. Client Portal Submissions & Pipeline Board
        print("\n[5/7] Seeding Client Portal Submissions & Pipeline Stages...")
        # Submit top candidates to Acme Cloud Systems
        submission_candidates = seeded_candidates[:4]
        pipeline_stages = ["CLIENT_SHORTLISTED", "INTERVIEW_REQUESTED", "SUBMITTED", "CLIENT_REJECTED"]

        for idx, (cand, stage) in enumerate(zip(submission_candidates, pipeline_stages)):
            sub_res = await session.execute(
                select(Submission).where(
                    Submission.candidate_id == cand.id,
                    Submission.requisition_id == target_req.id,
                    Submission.client_organization_id == client_org1.id,
                )
            )
            sub = sub_res.scalars().first()
            if not sub:
                ev_res = await session.execute(
                    select(Evaluation).where(
                        Evaluation.candidate_id == cand.id,
                        Evaluation.requisition_id == target_req.id,
                    )
                )
                cand_ev = ev_res.scalars().first()
                if not cand_ev:
                    continue

                ref_code = f"CND-{uuid.uuid4().hex[:6].upper()}"
                sub = Submission(
                    source_organization_id=staffing_org1.id,
                    requisition_id=target_req.id,
                    candidate_id=cand.id,
                    evaluation_id=cand_ev.id,
                    client_organization_id=client_org1.id,
                    submitted_by=recruiter1.id,
                    current_stage=stage,
                    custom_candidate_reference=ref_code,
                    recruiter_notes_for_client=f"Recommended candidate for {target_req.title}.",
                    status="active",
                )
                session.add(sub)
                await session.flush()

                # Pipeline history
                session.add(
                    PipelineRecord(
                        submission_id=sub.id,
                        current_stage="SUBMITTED",
                        changed_by=recruiter1.id,
                        reason_note="Initial client submission.",
                    )
                )
                if stage != "SUBMITTED":
                    session.add(
                        PipelineRecord(
                            submission_id=sub.id,
                            current_stage=stage,
                            previous_stage="SUBMITTED",
                            changed_by=client_hm1.id,
                            reason_note=f"Client status update: {stage}",
                        )
                    )

                # Client Request on the interview requested candidate
                if stage == "INTERVIEW_REQUESTED":
                    session.add(
                        ClientRequest(
                            submission_id=sub.id,
                            client_organization_id=client_org1.id,
                            requested_by=client_hm1.id,
                            request_type="INTERVIEW",
                            details="Client requesting 45-minute technical system design video interview next Tuesday.",
                            status="PENDING",
                        )
                    )

                print(f"  [+] Submissions pipeline: {ref_code} -> Stage: {stage} (Client: Acme Cloud Systems)")

        # 6. Candidate Consent & Audit Governance Records
        print("\n[6/7] Seeding Privacy Consent Records & Audit Logs...")
        for cand in seeded_candidates[:5]:
            c_rec_res = await session.execute(
                select(ConsentRecord).where(ConsentRecord.candidate_id == cand.id)
            )
            if not c_rec_res.scalars().first():
                session.add(
                    ConsentRecord(
                        candidate_id=cand.id,
                        organization_id=staffing_org1.id,
                        uploaded_by=recruiter1.id,
                        status=cand.consent_status,
                        purpose="resume_screening_and_shortlisting",
                        legal_basis="CONSENT",
                    )
                )

        # Audit logs for compliance verification
        session.add(
            AuditLog(
                organization_id=staffing_org1.id,
                actor_user_id=recruiter1.id,
                event_type="REQUISITION_CREATED",
                resource_type="Requisition",
                resource_id=target_req.id,
                payload_json={"title": target_req.title, "status": "active"},
            )
        )
        session.add(
            AuditLog(
                organization_id=staffing_org1.id,
                actor_user_id=recruiter1.id,
                event_type="BATCH_RESUMES_INGESTED",
                resource_type="UploadBatch",
                resource_id=uuid.uuid4(),
                payload_json={"count": len(candidate_specs), "status": "completed"},
            )
        )
        session.add(
            AuditLog(
                organization_id=client_org1.id,
                actor_user_id=client_hm1.id,
                event_type="CLIENT_SHORTLIST_DECISION",
                resource_type="Submission",
                resource_id=uuid.uuid4(),
                payload_json={"decision": "CLIENT_SHORTLISTED", "client": "Acme Cloud Systems"},
            )
        )
        print("  [+] Privacy consent histories and audit trails successfully created.")

        # Commit all operations
        await session.commit()

    print("\n[7/7] Seed verification complete!")
    print("==================================================")
    print("               Demo Accounts Ready                ")
    print("==================================================")
    print(f"  Recruiter:      recruiter@techrecruit.com   / {settings.SEED_RECRUITER_PASSWORD}")
    print(f"  Delivery Head:  head@techrecruit.com        / {settings.SEED_DELIVERY_PASSWORD}")
    print(f"  Client HM:      client@acme.com             / {settings.SEED_CLIENT_PASSWORD}")
    print(f"  Client HM (2):  client@starlight.com        / {settings.SEED_CLIENT_PASSWORD}")
    print("==================================================\n")


if __name__ == "__main__":
    asyncio.run(seed())
