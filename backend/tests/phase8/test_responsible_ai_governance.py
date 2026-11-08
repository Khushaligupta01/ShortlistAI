from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.evidence_extraction_service import evidence_extraction_service, ProtectedAttributeViolationError
from app.models.candidate import Candidate
from app.models.evaluation import Evaluation, RecruiterReview
from app.models.requisition import Requisition
from tests.conftest import auth_headers, create_test_org, seed_user_with_org


def test_protected_attribute_exclusion_guard():
    # 1. Candidate object - demographic attributes stripped
    candidate = Candidate(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        full_name="Alice Smith",
        email="alice@example.com",
    )
    clean_profile = evidence_extraction_service.clean_candidate_profile(candidate)
    assert "gender" not in clean_profile
    assert "age" not in clean_profile
    assert "date_of_birth" not in clean_profile
    assert "marital_status" not in clean_profile

    # 2. Assert that direct inclusion of protected attributes in scoring input raises error
    dirty_profile = {
        "candidate_id": str(candidate.id),
        "gender": "Female",
        "age": 34,
        "skills": ["Python"],
    }
    with pytest.raises(ProtectedAttributeViolationError):
        evidence_extraction_service.assert_no_protected_attributes(dirty_profile)


@pytest.mark.asyncio
async def test_governance_and_ai_metrics_endpoints(client: AsyncClient, db_session: AsyncSession):
    # Setup Recruiter & Staffing Org
    recruiter, org = await seed_user_with_org(
        db_session, email="rec_gov@staffing.com", password="Password123!", role="recruiter", org_name="Apex Governance Org"
    )
    recruiter_headers = auth_headers(recruiter.id, "recruiter", org.id)

    # Create Requisition & Candidates with evaluations
    req = Requisition(
        id=uuid.uuid4(),
        organization_id=org.id,
        created_by=recruiter.id,
        title="ML Engineer",
        job_description="PyTorch, Transformer, MLOps.",
        status="active",
    )
    db_session.add(req)

    cand1 = Candidate(
        id=uuid.uuid4(),
        organization_id=org.id,
        full_name="High Match Candidate",
        email="high@example.com",
    )
    cand2 = Candidate(
        id=uuid.uuid4(),
        organization_id=org.id,
        full_name="Med Match Candidate",
        email="med@example.com",
    )
    db_session.add_all([cand1, cand2])
    await db_session.flush()

    ev1 = Evaluation(
        id=uuid.uuid4(),
        candidate_id=cand1.id,
        requisition_id=req.id,
        scorecard_id=uuid.uuid4(),
        total_score=85.0,
        raw_score=85.0,
        normalized_score=85.0,
        evidence_coverage=90.0,
        evaluation_status="COMPLETED",
        confidence_level="HIGH",
    )
    ev2 = Evaluation(
        id=uuid.uuid4(),
        candidate_id=cand2.id,
        requisition_id=req.id,
        scorecard_id=uuid.uuid4(),
        total_score=62.0,
        raw_score=62.0,
        normalized_score=62.0,
        evidence_coverage=70.0,
        evaluation_status="COMPLETED",
        confidence_level="NEEDS_REVIEW",
    )
    db_session.add_all([ev1, ev2])
    await db_session.flush()

    # Recruiter review for ev1
    rev1 = RecruiterReview(
        id=uuid.uuid4(),
        evaluation_id=ev1.id,
        recruiter_id=recruiter.id,
        organization_id=org.id,
        decision="SHORTLIST",
        notes="Strong alignment with ML requirements.",
    )
    db_session.add(rev1)
    await db_session.commit()

    # 1. Test AI Metrics Endpoint
    metrics_res = await client.get("/api/v1/governance/ai-metrics", headers=recruiter_headers)
    assert metrics_res.status_code == 200, metrics_res.text
    metrics_data = metrics_res.json()
    assert metrics_data["total_evaluations"] >= 2
    assert metrics_data["score_distribution"]["high"] >= 1
    assert metrics_data["score_distribution"]["medium"] >= 1
    assert metrics_data["recruiter_review_distribution"]["SHORTLIST"] >= 1
    assert "fairness_and_bias_disclaimer" in metrics_data
    assert len(metrics_data["fairness_and_bias_disclaimer"]) > 20

    # 2. Test Evaluation Quality Endpoint
    qual_res = await client.get("/api/v1/governance/evaluation-quality", headers=recruiter_headers)
    assert qual_res.status_code == 200, qual_res.text
    qual_data = qual_res.json()
    assert qual_data["total_evaluations"] >= 2
    assert "confidence_breakdown" in qual_data
    assert len(qual_data["quality_assurance_notes"]) >= 3

    # 3. Test Privacy Dashboard Stats Endpoint
    dash_res = await client.get("/api/v1/privacy/dashboard", headers=recruiter_headers)
    assert dash_res.status_code == 200, dash_res.text
    dash_data = dash_res.json()
    assert "pending_consent_requests_count" in dash_data
    assert "granted_consents_count" in dash_data
    assert "completed_deletions_count" in dash_data
