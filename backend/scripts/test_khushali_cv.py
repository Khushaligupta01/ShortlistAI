import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import fitz
from app.ai.mock_provider import MockLLMProvider
from app.ai.evidence_extraction_service import EvidenceExtractionService
from app.ai.resume_extraction_service import ResumeExtractionService
from app.models.candidate import Candidate, CandidateSkill
from app.models.scorecard import ScorecardCriterion
from app.services.scoring_engine_service import ScoringEngine

async def run_evaluation():
    cv_path = r"c:\Users\gupta\OneDrive\Documents\Khushali_gupta_CV.pdf"
    doc = fitz.open(cv_path)
    resume_text = doc[0].get_text()

    print("=" * 60)
    print(" 1. RESUME PARSING (Offline Deterministic AI)")
    print("=" * 60)
    extractor = ResumeExtractionService(provider=MockLLMProvider())
    parsed = await extractor.extract_candidate_profile(resume_text)
    print(f"Full Name:        {parsed.full_name}")
    print(f"Email:            {parsed.email}")
    print(f"Phone:            {parsed.phone}")
    print(f"Location:         {parsed.location}")
    print(f"Total Exp:        {parsed.total_experience_years} years")
    print(f"Notice Period:    {parsed.notice_period_days} days")
    print(f"Extracted Skills: {', '.join([s.name for s in parsed.skills])}")

    print("\n" + "=" * 60)
    print(" 2. CRITERION EVIDENCE EXTRACTION AGAINST COMPANY A SCORECARD")
    print("=" * 60)
    criteria = [
        ScorecardCriterion(criterion_type="must_have_skill", criterion_name="Java", label="Java", weight=20, is_mandatory=True),
        ScorecardCriterion(criterion_type="must_have_skill", criterion_name="Spring Boot", label="Spring Boot", weight=20, is_mandatory=True),
        ScorecardCriterion(criterion_type="experience", criterion_name="5-8 Years Experience", label="Experience", weight=30, is_mandatory=True, config_json={"min_years": 5.0, "max_years": 8.0}),
        ScorecardCriterion(criterion_type="notice_period", criterion_name="Max 60 Days Notice", label="Notice", weight=15, is_mandatory=False, config_json={"max_notice_days": 60}),
        ScorecardCriterion(criterion_type="nice_to_have_skill", criterion_name="Python", label="Python", weight=10, is_mandatory=False),
        ScorecardCriterion(criterion_type="nice_to_have_skill", criterion_name="Docker", label="Docker", weight=5, is_mandatory=False),
    ]

    cand = Candidate(
        full_name=parsed.full_name,
        email=parsed.email,
        phone=parsed.phone,
        location=parsed.location,
        total_experience_years=parsed.total_experience_years,
        notice_period_days=parsed.notice_period_days,
    )
    cand.skills = [CandidateSkill(name=s.name, raw_name=s.raw_name, evidence=s.evidence) for s in parsed.skills]

    evidence_service = EvidenceExtractionService(provider=MockLLMProvider())
    evidence_items = await evidence_service.extract_evidence(cand, criteria, resume_text)

    for item in evidence_items:
        print(f"\nCriterion: [{item.criterion_name}] (Status: {item.match_status}, Confidence: {item.confidence})")
        print(f"  Quoted Excerpt: \"{item.evidence_text}\"")
        print(f"  Source Reference: {item.source_reference}")

    from app.models.scorecard import Scorecard
    scorecard = Scorecard(
        total_weight=100,
        experience_min=5.0,
        experience_max=8.0,
        max_notice_days=60,
        location="Noida",
        scoring_config={
            "experience": 30,
            "must_have_skills": 40,
            "notice_period": 15,
            "location": 10,
            "nice_to_have_skills": 5,
        },
    )
    scorecard.criteria = criteria
    for i, c in enumerate(criteria):
        c.id = evidence_items[i].criterion_id

    print("\n" + "=" * 60)
    print(" 3. DETERMINISTIC SCORING ENGINE RESULT")
    print("=" * 60)
    engine = ScoringEngine()
    score_result = engine.compute_scores(cand, scorecard, evidence_items)
    print(f"Normalized Score:    {score_result.normalized_score} / 100.0")
    print(f"Raw Awarded Points:  {score_result.raw_score} / 100.0")
    print(f"Confidence Level:    {score_result.confidence_level}")
    print(f"Evidence Coverage:   {score_result.evidence_coverage}%")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_evaluation())
