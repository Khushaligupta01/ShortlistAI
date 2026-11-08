from __future__ import annotations

import logging
import re
import uuid
from typing import Any, Dict, List, Optional, Set

from app.ai.prompts import build_evidence_extraction_prompt
from app.ai.provider import LLMExtractionError, LLMProvider, LLMProviderUnavailableError
from app.ai.provider_factory import get_llm_provider
from app.ai.schemas import CandidateEvidenceExtractionResult, CriterionEvidenceItem
from app.core.config import settings
from app.models.candidate import Candidate
from app.models.scorecard import ScorecardCriterion
from app.services.skill_normalization_service import skill_normalizer

logger = logging.getLogger("shortlistai.evidence_extraction")


class ProtectedAttributeViolationError(ValueError):
    """Raised when protected attributes are detected in evaluation inputs."""
    pass


PROTECTED_ATTRIBUTES: Set[str] = {
    "name",
    "full_name",
    "first_name",
    "last_name",
    "gender",
    "sex",
    "age",
    "date_of_birth",
    "dob",
    "photograph",
    "photo",
    "marital_status",
    "marital",
    "ethnicity",
    "race",
    "religion",
    "nationality",
    "national_id",
    "ssn",
    "email",
    "phone",
}


class EvidenceExtractionService:
    """
    Service responsible for extracting factual, criterion-level evidence
    by evaluating candidate professional history against approved scorecard criteria.
    Enforces protected attribute exclusion and anti-fabrication grounding.
    """

    def __init__(self, provider: Optional[LLMProvider] = None) -> None:
        self._provider = provider

    def _get_provider(self) -> LLMProvider:
        if self._provider is not None:
            return self._provider
        return get_llm_provider(settings.AI_PROVIDER)

    def clean_candidate_profile(self, candidate: Candidate) -> Dict[str, Any]:
        """
        Creates a clean candidate profile dictionary with all protected personal
        attributes strictly stripped out.
        """
        clean = {
            "total_experience_years": float(candidate.total_experience_years) if candidate.total_experience_years is not None else None,
            "location": candidate.location,
            "notice_period_days": candidate.notice_period_days,
            "skills": [
                {
                    "raw_name": s.raw_name,
                    "normalized_name": getattr(s, "name", s.raw_name),
                    "evidence": s.evidence,
                }
                for s in (candidate.skills or [])
            ],
            "employments": [
                {
                    "company": e.company,
                    "job_title": e.job_title,
                    "start_date": e.start_date,
                    "end_date": e.end_date,
                    "is_current": e.is_current,
                    "description": e.description,
                    "technologies": e.technologies or [],
                }
                for e in (candidate.employments or [])
            ],
            "educations": [
                {
                    "institution": ed.institution,
                    "qualification": ed.qualification,
                    "field_of_study": ed.field_of_study,
                    "graduation_year": ed.graduation_year,
                }
                for ed in (candidate.educations or [])
            ],
            "certifications": candidate.certifications or [],
        }

        # Runtime verification check
        self.assert_no_protected_attributes(clean)
        return clean

    def assert_no_protected_attributes(self, profile_dict: Dict[str, Any]) -> None:
        """
        Defense-in-depth runtime assertion ensuring no protected attributes exist
        in evaluation inputs.
        """
        for k in profile_dict.keys():
            if k.lower() in PROTECTED_ATTRIBUTES:
                raise ProtectedAttributeViolationError(
                    f"Protected personal attribute '{k}' detected in candidate evaluation input."
                )

    def verify_excerpt_against_resume(self, excerpt: str, resume_text: str) -> bool:
        """
        Anti-fabrication check: verifies whether an AI-cited excerpt actually appears
        in the extracted resume text (case-insensitive token overlap or substring).
        """
        if not excerpt or not resume_text:
            return False

        clean_excerpt = excerpt.strip().lower()
        clean_resume = resume_text.lower()

        # 1. Exact or normalized substring match
        if clean_excerpt in clean_resume:
            return True

        # 2. Token overlap check (>= 75% of meaningful tokens must appear in resume)
        tokens = [t for t in re.findall(r"\b\w+\b", clean_excerpt) if len(t) > 2]
        if not tokens:
            return False

        matches = sum(1 for t in tokens if t in clean_resume)
        overlap = matches / len(tokens)
        return overlap >= 0.75

    async def extract_evidence(
        self,
        candidate: Candidate,
        criteria: List[ScorecardCriterion],
        resume_text: str = "",
    ) -> List[CriterionEvidenceItem]:
        """
        Extract criterion-level evidence for a candidate against a list of scorecard criteria.
        Uses AI provider when available, falling back to deterministic zero-hallucination extractor.
        """
        clean_profile = self.clean_candidate_profile(candidate)

        criteria_dicts = [
            {
                "criterion_id": str(c.id),
                "criterion_type": c.criterion_type,
                "criterion_name": c.criterion_name,
                "label": c.label,
                "description": c.description,
                "weight": c.weight,
                "is_mandatory": c.is_mandatory,
                "config": c.config_json or {},
            }
            for c in criteria
        ]

        # Attempt AI provider extraction if configured
        try:
            provider = self._get_provider()
            prompt = build_evidence_extraction_prompt(
                clean_candidate_profile=clean_profile,
                criteria=criteria_dicts,
                resume_text=resume_text or "",
            )
            raw_response = await provider.extract_evidence(
                prompt=prompt,
                output_schema=CandidateEvidenceExtractionResult.model_json_schema(),
                max_tokens=2500,
            )

            result = CandidateEvidenceExtractionResult.model_validate(raw_response)
            items_by_id = {item.criterion_id: item for item in result.criteria_evidence}

            # Anti-fabrication verification
            validated_items: List[CriterionEvidenceItem] = []
            for c in criteria:
                cid = str(c.id)
                if cid in items_by_id:
                    item = items_by_id[cid]
                    # Verify excerpt against resume text
                    if item.evidence_text and item.match_status in ("MATCHED", "PARTIAL"):
                        is_verified = self.verify_excerpt_against_resume(item.evidence_text, resume_text)
                        if not is_verified:
                            logger.warning(
                                f"Excerpt for criterion '{c.criterion_name}' could not be verified in resume text: {item.evidence_text[:100]}"
                            )
                            # Flag unverified excerpt
                            item.confidence = min(item.confidence, 0.49)
                            item.explanation = (
                                f"[Unverified Excerpt] {item.explanation or ''}".strip()
                            )
                    validated_items.append(item)
                else:
                    # Fallback for any missing criterion in AI response
                    fallback_item = self._extract_criterion_deterministic(candidate, c, resume_text)
                    validated_items.append(fallback_item)

            return validated_items

        except (LLMProviderUnavailableError, LLMExtractionError, Exception) as exc:
            logger.info(
                f"Using deterministic evidence extractor for candidate {candidate.id}: {exc}"
            )
            return [
                self._extract_criterion_deterministic(candidate, c, resume_text)
                for c in criteria
            ]

    def _extract_criterion_deterministic(
        self,
        candidate: Candidate,
        criterion: ScorecardCriterion,
        resume_text: str = "",
    ) -> CriterionEvidenceItem:
        """
        Deterministic, zero-hallucination fallback evidence extractor based strictly
        on validated candidate records and extracted resume text.
        """
        cid = str(criterion.id)
        c_type = criterion.criterion_type
        c_name = criterion.criterion_name or criterion.label
        cfg = criterion.config_json or {}

        # -------------------------------------------------------------
        # 1. Experience Criterion
        # -------------------------------------------------------------
        if c_type == "experience":
            min_years = cfg.get("min_years") or cfg.get("experience_min") or 0.0
            max_years = cfg.get("max_years") or cfg.get("experience_max") or 99.0

            if candidate.total_experience_years is None:
                return CriterionEvidenceItem(
                    criterion_id=cid,
                    criterion_name=c_name,
                    match_status="UNKNOWN",
                    evidence_text=None,
                    source_reference=None,
                    confidence=0.50,
                    explanation="Resume does not explicitly state total years of experience.",
                )

            years = float(candidate.total_experience_years)
            if years >= min_years:
                return CriterionEvidenceItem(
                    criterion_id=cid,
                    criterion_name=c_name,
                    match_status="MATCHED",
                    evidence_text=f"Total verifiable experience: {years:.1f} years.",
                    source_reference="Employment History",
                    confidence=0.95,
                    explanation=f"Candidate has {years:.1f} years experience, meeting the required minimum of {min_years} years.",
                )
            else:
                return CriterionEvidenceItem(
                    criterion_id=cid,
                    criterion_name=c_name,
                    match_status="PARTIAL",
                    evidence_text=f"Total experience: {years:.1f} years (below required {min_years} years).",
                    source_reference="Employment History",
                    confidence=0.90,
                    explanation=f"Candidate has {years:.1f} years experience, which is below the minimum required {min_years} years.",
                )

        # -------------------------------------------------------------
        # 2. Skills (Must-Have or Nice-To-Have)
        # -------------------------------------------------------------
        elif c_type in ("must_have_skill", "nice_to_have_skill"):
            target_skill = c_name

            # Check candidate structured skills
            for s in candidate.skills or []:
                s_name = getattr(s, "name", "")
                if skill_normalizer.is_match(s.raw_name, target_skill) or (s_name and skill_normalizer.is_match(s_name, target_skill)):
                    return CriterionEvidenceItem(
                        criterion_id=cid,
                        criterion_name=c_name,
                        match_status="MATCHED",
                        evidence_text=s.evidence or f"Explicit skill listed: {s.raw_name}",
                        source_reference="Skills & Technologies",
                        confidence=0.95,
                        explanation=f"Direct match found for skill '{c_name}'.",
                    )

            # Check candidate employment technologies
            for emp in candidate.employments or []:
                for tech in emp.technologies or []:
                    if skill_normalizer.is_match(tech, target_skill):
                        return CriterionEvidenceItem(
                            criterion_id=cid,
                            criterion_name=c_name,
                            match_status="MATCHED",
                            evidence_text=f"Used {tech} at {emp.company} ({emp.job_title}): {emp.description or ''}"[:300],
                            source_reference=f"Employment: {emp.company}",
                            confidence=0.92,
                            explanation=f"Applied skill '{c_name}' at {emp.company}.",
                        )

            # Check resume text for explicit whole-word mentions
            norm_target = skill_normalizer.normalize(target_skill)
            # Strict boundary check (ensures Spring != Spring Boot)
            if norm_target == "spring_boot":
                pattern = r"\bspring\s*[-_]?\s*boot\b"
            elif norm_target == "spring_framework":
                # Matches "spring framework" or standalone "spring" but NOT "spring boot"
                pattern = r"\bspring\b(?!\s*[-_]?\s*boot)"
            elif norm_target == "java":
                # Java but NOT JavaScript
                pattern = r"\bjava\b(?!\s*script)"
            else:
                escaped = re.escape(c_name.strip())
                pattern = rf"\b{escaped}\b"

            if resume_text:
                match = re.search(pattern, resume_text, re.IGNORECASE)
                if match:
                    # Extract 150-char window around match
                    start = max(0, match.start() - 50)
                    end = min(len(resume_text), match.end() + 100)
                    excerpt = resume_text[start:end].strip()
                    return CriterionEvidenceItem(
                        criterion_id=cid,
                        criterion_name=c_name,
                        match_status="MATCHED",
                        evidence_text=excerpt,
                        source_reference="Resume Text",
                        confidence=0.85,
                        explanation=f"Explicit mention of '{c_name}' verified in resume text.",
                    )

            # Not matched
            return CriterionEvidenceItem(
                criterion_id=cid,
                criterion_name=c_name,
                match_status="NOT_MATCHED",
                evidence_text=None,
                source_reference=None,
                confidence=0.90,
                explanation=f"No evidence found in resume for skill '{c_name}'.",
            )

        # -------------------------------------------------------------
        # 3. Notice Period Criterion
        # -------------------------------------------------------------
        elif c_type == "notice_period":
            max_notice_days = cfg.get("max_notice_days") or 60

            if candidate.notice_period_days is None:
                return CriterionEvidenceItem(
                    criterion_id=cid,
                    criterion_name=c_name,
                    match_status="UNKNOWN",
                    evidence_text=None,
                    source_reference=None,
                    confidence=0.50,
                    explanation="Notice period not explicitly stated in resume.",
                )

            cand_notice = candidate.notice_period_days
            if cand_notice <= max_notice_days:
                return CriterionEvidenceItem(
                    criterion_id=cid,
                    criterion_name=c_name,
                    match_status="MATCHED",
                    evidence_text=f"Candidate notice period: {cand_notice} days.",
                    source_reference="Candidate Profile",
                    confidence=0.95,
                    explanation=f"Notice period of {cand_notice} days is within maximum required {max_notice_days} days.",
                )
            else:
                return CriterionEvidenceItem(
                    criterion_id=cid,
                    criterion_name=c_name,
                    match_status="PARTIAL",
                    evidence_text=f"Candidate notice period: {cand_notice} days (exceeds {max_notice_days} days).",
                    source_reference="Candidate Profile",
                    confidence=0.90,
                    explanation=f"Notice period of {cand_notice} days exceeds maximum required {max_notice_days} days.",
                )

        # -------------------------------------------------------------
        # 4. Location Criterion
        # -------------------------------------------------------------
        elif c_type == "location":
            target_loc = (cfg.get("location") or c_name or "").strip().lower()

            if not candidate.location:
                return CriterionEvidenceItem(
                    criterion_id=cid,
                    criterion_name=c_name,
                    match_status="UNKNOWN",
                    evidence_text=None,
                    source_reference=None,
                    confidence=0.50,
                    explanation="Candidate location not stated in resume.",
                )

            cand_loc = candidate.location.strip().lower()
            if target_loc in cand_loc or cand_loc in target_loc or "remote" in cand_loc:
                return CriterionEvidenceItem(
                    criterion_id=cid,
                    criterion_name=c_name,
                    match_status="MATCHED",
                    evidence_text=f"Candidate location: {candidate.location}",
                    source_reference="Candidate Profile",
                    confidence=0.95,
                    explanation=f"Location matches required location '{c_name}'.",
                )
            else:
                return CriterionEvidenceItem(
                    criterion_id=cid,
                    criterion_name=c_name,
                    match_status="NOT_MATCHED",
                    evidence_text=f"Candidate location: {candidate.location}",
                    source_reference="Candidate Profile",
                    confidence=0.90,
                    explanation=f"Candidate location '{candidate.location}' does not match required location '{c_name}'.",
                )

        # Default fallback
        return CriterionEvidenceItem(
            criterion_id=cid,
            criterion_name=c_name,
            match_status="UNKNOWN",
            evidence_text=None,
            source_reference=None,
            confidence=0.50,
            explanation=f"Insufficient information to evaluate criterion '{c_name}'.",
        )


evidence_extraction_service = EvidenceExtractionService()
