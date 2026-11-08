from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate, CandidateEmployment, CandidateEducation, CandidateSkill
from app.models.candidate_note import CandidateNote
from app.models.evaluation import Evaluation, EvaluationEvidence
from app.models.requisition import Requisition
from app.models.scorecard import Scorecard, ScorecardCriterion
from app.models.submission import Submission
from tests.conftest import auth_headers, create_test_org, seed_user_with_org


@pytest.mark.asyncio
async def test_candidate_masking_and_privacy_guarantees(client: AsyncClient, db_session: AsyncSession):
    # 1. Setup recruiter and client
    recruiter, staffing_org = await seed_user_with_org(
        db_session, email="rec_privacy@staffing.com", password="Password123!", role="recruiter", org_name="Privacy Staffing Firm"
    )
    client_org = await create_test_org(db_session, name="Global Fintech Client", org_type="client_company")
    client_user, _ = await seed_user_with_org(
        db_session, email="hiring_privacy@fintech.com", password="Password123!", role="client_hiring_manager", org_name="Global Fintech Client"
    )
    client_headers = auth_headers(client_user.id, "client_hiring_manager", client_org.id)

    # 2. Requisition and Scorecard
    req = Requisition(
        id=uuid.uuid4(),
        organization_id=staffing_org.id,
        created_by=recruiter.id,
        title="Staff Security Engineer",
        job_description="Application security, threat modeling, and cryptography.",
        status="active",
        client_organization_id=client_org.id,
    )
    db_session.add(req)
    await db_session.commit()

    sc = Scorecard(
        id=uuid.uuid4(),
        requisition_id=req.id,
        status="approved",
        version_number=1,
    )
    db_session.add(sc)
    await db_session.commit()

    crit = ScorecardCriterion(
        id=uuid.uuid4(),
        scorecard_id=sc.id,
        criterion_type="must_have",
        criterion_name="AppSec Mastery",
        label="Application Security",
        weight=40,
    )
    db_session.add(crit)
    await db_session.commit()

    # 3. Create Candidate with sensitive PII, street address, and internal recruiter notes
    cand = Candidate(
        id=uuid.uuid4(),
        organization_id=staffing_org.id,
        full_name="Edward Joseph Snowden",
        email="edward.secret@protonmail.com",
        phone="+1 (555) 867-5309",
        location="1400 Defense Highway, Suite 402, Fort Meade, MD 20755",
        total_experience_years=8.5,
        notice_period_days=30,
    )
    db_session.add(cand)
    await db_session.commit()

    # Add candidate employments and educations
    emp = CandidateEmployment(
        id=uuid.uuid4(),
        candidate_id=cand.id,
        job_title="Infrastructure Security Lead",
        company="NSA Contractor Booz Allen",
        start_date="2018-01-01",
        end_date="2022-05-31",
        is_current=False,
        description="Audited cryptographic modules and distributed key stores.",
    )
    edu = CandidateEducation(
        id=uuid.uuid4(),
        candidate_id=cand.id,
        qualification="B.S.",
        institution="University of Maryland",
        field_of_study="Computer Engineering",
        graduation_year=2014,
    )
    skill = CandidateSkill(
        id=uuid.uuid4(),
        candidate_id=cand.id,
        name="Cryptography",
        raw_name="Cryptography",
    )
    db_session.add_all([emp, edu, skill])
    await db_session.commit()

    # Private internal recruiter note (Phase 6 feature - MUST NEVER LEAK TO CLIENT)
    priv_note = CandidateNote(
        id=uuid.uuid4(),
        candidate_id=cand.id,
        requisition_id=req.id,
        author_id=recruiter.id,
        organization_id=staffing_org.id,
        content="CONFIDENTIAL: Candidate requested $210k base and has visa renewal pending in September.",
    )
    db_session.add(priv_note)
    await db_session.commit()

    # Evaluation with evidence
    eval_obj = Evaluation(
        id=uuid.uuid4(),
        candidate_id=cand.id,
        requisition_id=req.id,
        scorecard_id=sc.id,
        scorecard_version=1,
        total_score=94.0,
        raw_score=94.0,
        normalized_score=94.0,
        evaluation_status="completed",
    )
    db_session.add(eval_obj)
    await db_session.commit()

    ev_item = EvaluationEvidence(
        id=uuid.uuid4(),
        evaluation_id=eval_obj.id,
        scorecard_criterion_id=crit.id,
        evidence_status="MATCH",
        confidence_score=1.0,
        evidence_text="Audited cryptographic modules and distributed key stores.",
        explanation="Proven hands-on security architecture experience.",
    )
    db_session.add(ev_item)
    await db_session.commit()

    # Create submission
    sub = Submission(
        id=uuid.uuid4(),
        candidate_id=cand.id,
        requisition_id=req.id,
        evaluation_id=eval_obj.id,
        submitted_by=recruiter.id,
        source_organization_id=staffing_org.id,
        client_organization_id=client_org.id,
        status="active",
        current_stage="SUBMITTED",
        custom_candidate_reference="Candidate CND-SEC40",
        recruiter_notes_for_client="Strong candidate with leading industry cryptographic knowledge.",
    )
    db_session.add(sub)
    await db_session.commit()

    # 4. Client queries masked profile
    res = await client.get(f"/api/v1/client/submissions/{sub.id}", headers=client_headers)
    assert res.status_code == 200
    data = res.json()

    # 5. VERIFY STRICT ZERO-PII GUARANTEE
    # Full name MUST NOT be present anywhere in the response
    assert data["candidate_reference"] == "Candidate CND-SEC40"
    raw_response_text = str(data).lower()

    assert "snowden" not in raw_response_text
    assert "edward" not in raw_response_text
    assert "protonmail" not in raw_response_text
    assert "867-5309" not in raw_response_text
    assert "1400 defense highway" not in raw_response_text
    assert "confidential: candidate requested" not in raw_response_text
    assert "visa renewal pending" not in raw_response_text

    # Location sanitized
    assert "1400 Defense Highway" not in data["location"]

    # Recruiter notes for client IS present
    assert data["recruiter_notes_for_client"] == "Strong candidate with leading industry cryptographic knowledge."

    # Evidence item has status and text, but NO internal weight numbers
    assert len(data["criterion_evaluations"]) == 1
    crit_ev = data["criterion_evaluations"][0]
    assert crit_ev["status"] == "MATCH"
    assert crit_ev["criterion_name"] == "AppSec Mastery"
    assert "weight" not in crit_ev

    # Experience and skills present
    assert len(data["employments"]) == 1
    assert data["employments"][0]["title"] == "Infrastructure Security Lead"
    assert "Cryptography" in data["skills"]
