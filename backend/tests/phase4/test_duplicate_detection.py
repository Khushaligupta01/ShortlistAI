from __future__ import annotations

import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.resume import Resume
from app.services.duplicate_detection_service import DuplicateDetectionService
from tests.conftest import create_test_org


@pytest.fixture
def detector():
    return DuplicateDetectionService()


@pytest.mark.asyncio
async def test_exact_file_duplicate_detection(db_session: AsyncSession, detector: DuplicateDetectionService):
    org = await create_test_org(db_session, name="Dedup Org 1")
    file_hash = "a" * 64

    # Create original resume
    resume1 = Resume(
        organization_id=org.id,
        file_name="original.pdf",
        storage_path="path/1.pdf",
        file_hash=file_hash,
        mime_type="application/pdf",
        file_size_bytes=1000,
        parse_status="parsed",
    )
    db_session.add(resume1)
    await db_session.commit()

    # Check duplicate
    match = await detector.check_exact_file_duplicate(db_session, org.id, file_hash)
    assert match.is_duplicate is True
    assert match.duplicate_type == "exact_file"
    assert match.existing_resume_id == resume1.id
    assert match.confidence == 1.0


@pytest.mark.asyncio
async def test_cross_org_file_duplicate_isolation(db_session: AsyncSession, detector: DuplicateDetectionService):
    org1 = await create_test_org(db_session, name="Org A")
    org2 = await create_test_org(db_session, name="Org B")
    file_hash = "b" * 64

    # Org 1 uploads
    resume1 = Resume(
        organization_id=org1.id,
        file_name="resume_org1.pdf",
        storage_path="path/org1.pdf",
        file_hash=file_hash,
        mime_type="application/pdf",
        file_size_bytes=1000,
        parse_status="parsed",
    )
    db_session.add(resume1)
    await db_session.commit()

    # Org 2 checks same hash -> should NOT match (cross-org isolation)
    match_org2 = await detector.check_exact_file_duplicate(db_session, org2.id, file_hash)
    assert match_org2.is_duplicate is False


@pytest.mark.asyncio
async def test_candidate_duplicate_by_email(db_session: AsyncSession, detector: DuplicateDetectionService):
    org = await create_test_org(db_session, name="Cand Org 1")

    candidate = Candidate(
        organization_id=org.id,
        full_name="John Doe",
        email="john.doe@example.com",
        phone="+15550199",
    )
    db_session.add(candidate)
    await db_session.commit()

    # Check match with case/whitespace variations
    match = await detector.check_candidate_match(
        db_session, org.id, email="  JOHN.DOE@example.com ", phone=None
    )
    assert match.is_duplicate is True
    assert match.duplicate_type == "confirmed_candidate"
    assert match.existing_candidate_id == candidate.id
    assert match.confidence >= 0.95


@pytest.mark.asyncio
async def test_candidate_duplicate_by_phone(db_session: AsyncSession, detector: DuplicateDetectionService):
    org = await create_test_org(db_session, name="Cand Org 2")

    candidate = Candidate(
        organization_id=org.id,
        full_name="Alice Smith",
        email="alice@firstcompany.com",
        phone="+1 (555) 987-6543",
    )
    db_session.add(candidate)
    await db_session.commit()

    # Different email but same phone
    match = await detector.check_candidate_match(
        db_session, org.id, email="alice.new@personal.com", phone="555-987-6543"
    )
    assert match.is_duplicate is True
    assert match.duplicate_type == "potential_candidate"
    assert match.existing_candidate_id == candidate.id


@pytest.mark.asyncio
async def test_similar_name_different_email_not_merged(db_session: AsyncSession, detector: DuplicateDetectionService):
    org = await create_test_org(db_session, name="Cand Org 3")

    candidate = Candidate(
        organization_id=org.id,
        full_name="David Miller",
        email="david.m@company.com",
        phone="5550100",
    )
    db_session.add(candidate)
    await db_session.commit()

    # Different candidate with same common name
    match = await detector.check_candidate_match(
        db_session, org.id, email="david.m.different@domain.com", phone="5550200"
    )
    # Never auto-merge based on name alone
    assert match.is_duplicate is False


def test_text_similarity_calculation(detector: DuplicateDetectionService):
    text_a = "Senior Java Engineer with 8 years experience building Spring Boot microservices and Kafka"
    text_b = "Java Engineer with 8 years experience designing Spring Boot microservices and Kafka pipelines"
    score = detector.calculate_text_similarity(text_a, text_b)
    assert score > 0.70

    unrelated = "Digital Marketing Executive SEO Content Strategy Google Analytics"
    score_unrelated = detector.calculate_text_similarity(text_a, unrelated)
    assert score_unrelated < 0.10
