from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from app.ai.prompts import build_resume_extraction_prompt
from app.ai.provider import LLMExtractionError, LLMProvider, LLMProviderUnavailableError
from app.ai.provider_factory import get_provider
from app.ai.schemas import (
    CandidateCertificationItem,
    CandidateEducationItem,
    CandidateEmploymentItem,
    CandidateSkillItem,
    ResumeExtractionResult,
)
from app.core.config import settings

logger = logging.getLogger("shortlistai.ai.resume_extraction")


class ResumeExtractionService:
    """Orchestrates structured resume extraction using the configured AI provider."""

    def __init__(self, provider: LLMProvider | None = None) -> None:
        self._provider = provider

    def _get_provider(self) -> LLMProvider:
        if self._provider is None:
            self._provider = get_provider()
        return self._provider

    async def extract_candidate_profile(
        self,
        resume_text: str,
    ) -> ResumeExtractionResult:
        if not resume_text or not resume_text.strip():
            return ResumeExtractionResult(
                warnings=["Resume text is empty."],
                missing_fields=["full_name", "email", "phone", "skills", "employment_history"],
            )

        provider = self._get_provider()

        try:
            prompt = build_resume_extraction_prompt(resume_text)
            schema_dict = ResumeExtractionResult.model_json_schema()

            raw_result = await provider.extract_resume(
                prompt=prompt,
                output_schema=schema_dict,
                max_tokens=settings.AI_MAX_OUTPUT_TOKENS,
            )

            # Strict Pydantic validation
            validated = ResumeExtractionResult.model_validate(raw_result)

            # Ensure missing fields list accurately reflects nulls
            self._populate_missing_fields(validated)
            return validated

        except LLMProviderUnavailableError:
            logger.info("AI provider is unavailable. Performing deterministic baseline extraction.")
            return self._fallback_deterministic_extraction(resume_text)
        except LLMExtractionError as e:
            logger.warning("LLM extraction failed: %s. Using deterministic baseline.", e)
            result = self._fallback_deterministic_extraction(resume_text)
            result.warnings.append(f"AI extraction unavailable ({e.args[0] if e.args else 'Error'}). Parsed with rule-based engine.")
            return result
        except Exception as e:
            logger.exception("Unexpected error during resume extraction")
            result = self._fallback_deterministic_extraction(resume_text)
            result.warnings.append(f"Parsing error: {str(e)}")
            return result

    def _populate_missing_fields(self, result: ResumeExtractionResult) -> None:
        missing = set(result.missing_fields)
        if not result.full_name:
            missing.add("full_name")
        if not result.email:
            missing.add("email")
        if not result.phone:
            missing.add("phone")
        if not result.location:
            missing.add("location")
        if result.notice_period_days is None:
            missing.add("notice_period_days")
        if result.total_experience_years is None:
            missing.add("total_experience_years")
        if not result.skills:
            missing.add("skills")
        if not result.employment_history:
            missing.add("employment_history")
        if not result.education:
            missing.add("education")
        result.missing_fields = sorted(list(missing))

    def _fallback_deterministic_extraction(self, text: str) -> ResumeExtractionResult:
        """
        Deterministic, zero-hallucination baseline extractor.
        Uses exact regular expressions for contact info and explicit skills.
        Never fabricates employment, education, or notice period.
        """
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        # 1. Email extraction (RFC compliant regex)
        email_match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b", text)
        email = email_match.group(0) if email_match else None

        # 2. Phone extraction (standard international/local formats)
        phone_match = re.search(r"(\+?\d{1,3}[-.\s]?)?(\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}\b", text)
        phone = phone_match.group(0).strip() if phone_match and len(re.sub(r"\D", "", phone_match.group(0))) >= 7 else None

        # 3. Name candidate: first non-header, non-contact line of reasonable length
        full_name = None
        for line in lines[:5]:
            if not email or email not in line:
                if not phone or phone not in line:
                    if len(line.split()) in (2, 3, 4) and not any(kw in line.lower() for kw in ["curriculum", "resume", "page", "cv", "profile", "summary"]):
                        full_name = line.strip()
                        break

        # 4. Notice period if explicitly stated (e.g., "Notice period: 30 days", "Immediate joiner")
        notice_period_days = None
        np_match = re.search(r"notice\s*(?:period)?\s*[:=-]?\s*(\d{1,3})\s*days?", text, re.IGNORECASE)
        if np_match:
            try:
                notice_period_days = int(np_match.group(1))
            except ValueError:
                pass
        elif re.search(r"\b(?:immediate(?:ly)?\s*(?:available|joiner)?|0\s*days?\s*notice)\b", text, re.IGNORECASE):
            notice_period_days = 0

        # 5. Common skill keywords mentioned verbatim in text
        KNOWN_SKILLS = [
            "Java", "Spring Boot", "Python", "Django", "FastAPI", "JavaScript", "TypeScript",
            "React", "Node.js", "Docker", "Kubernetes", "AWS", "SQL", "PostgreSQL",
            "MongoDB", "Redis", "Kafka", "Git", "REST API", "Microservices", "C++", "C#", ".NET"
        ]
        found_skills: List[CandidateSkillItem] = []
        seen_skills = set()
        for s in KNOWN_SKILLS:
            # Word boundary regex for exact matching
            pattern = r"(?<!\w)" + re.escape(s) + r"(?!\w)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                norm = s.lower()
                if norm not in seen_skills:
                    seen_skills.add(norm)
                    # Get surrounding snippet as evidence
                    start = max(0, match.start() - 30)
                    end = min(len(text), match.end() + 30)
                    snippet = text[start:end].replace("\n", " ").strip()
                    found_skills.append(
                        CandidateSkillItem(
                            name=norm,
                            raw_name=s,
                            evidence=f"...{snippet}...",
                        )
                    )

        # 6. Education detection via common keywords
        found_education: List[CandidateEducationItem] = []
        edu_keywords = ["Bachelor", "Master", "B.Tech", "B.E.", "M.Tech", "BS", "MS", "PhD", "Degree"]
        for line in lines:
            if any(k.lower() in line.lower() for k in edu_keywords):
                # Try to extract year (4 digits between 1970 and 2030)
                yr_match = re.search(r"\b(19\d{2}|20[0-2]\d)\b", line)
                year = int(yr_match.group(1)) if yr_match else None
                found_education.append(
                    CandidateEducationItem(
                        institution=line[:250],
                        qualification="Degree",
                        field_of_study=None,
                        graduation_year=year,
                    )
                )
                if len(found_education) >= 3:
                    break

        result = ResumeExtractionResult(
            full_name=full_name,
            email=email,
            phone=phone,
            location=None,
            notice_period_days=notice_period_days,
            total_experience_years=None,
            skills=found_skills,
            employment_history=[],
            education=found_education,
            certifications=[],
            warnings=["AI provider not configured; deterministic rule-based extraction applied."],
            missing_fields=[],
        )
        self._populate_missing_fields(result)
        return result


resume_extraction_service = ResumeExtractionService()

