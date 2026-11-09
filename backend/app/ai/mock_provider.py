"""
Deterministic, rule-based Mock/Test AI Provider for ShortlistAI.

Provides structurally valid, non-fabricated extractions for automated test suites,
CI/CD environments, and offline local development without requiring external API keys
or network calls.

Strictly rejected in production environments.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from app.ai.provider import LLMProvider
from app.ai.schemas import (
    CandidateCertificationItem,
    CandidateEducationItem,
    CandidateEmploymentItem,
    CandidateEvidenceExtractionResult,
    CandidateSkillItem,
    CriterionEvidenceItem,
    ExperienceRequirement,
    ExtractionWarning,
    JDExtractionResult,
    NoticePeriodRequirement,
    ResumeExtractionResult,
    SkillRequirement,
)
from app.core.config import Settings

logger = logging.getLogger("shortlistai.ai.mock_provider")

COMMON_SKILLS = [
    "Python", "FastAPI", "Django", "Flask", "Java", "Spring Boot", "React",
    "TypeScript", "JavaScript", "SQL", "PostgreSQL", "MySQL", "MongoDB",
    "Redis", "Kafka", "Docker", "Kubernetes", "AWS", "Azure", "GCP",
    "CI/CD", "Git", "REST", "GraphQL", "Microservices", "C++", "Go",
]


class MockLLMProvider(LLMProvider):
    """
    Deterministic mock AI provider for testing and offline development.
    Satisfies the LLMProvider protocol by returning schema-compliant dictionaries.
    """

    def __init__(self, config: Optional[Settings] = None) -> None:
        self.config = config
        self.name = "mock"
        logger.info("Initialized MockLLMProvider for offline/test execution.")

    async def extract_jd(
        self,
        prompt: str,
        output_schema: dict[str, Any],
        max_tokens: int,
    ) -> dict[str, Any]:
        """
        Extract structured requirements from job description text using
        deterministic heuristic scanning.
        """
        text = prompt
        text_lower = text.lower()

        # Job title heuristic
        job_title = "Software Engineer"
        for title in [
            "Senior Backend Engineer", "Senior Java Developer", "Senior Java Dev",
            "Full Stack Engineer", "Backend Engineer", "Frontend Engineer",
            "DevOps Engineer", "Data Engineer", "Python Developer",
        ]:
            if title.lower() in text_lower:
                job_title = title
                break

        # Experience extraction
        exp_match = re.search(r"(\d+)\+?\s*(?:-\s*(\d+))?\s*years?", text_lower)
        min_years = int(exp_match.group(1)) if exp_match else 3
        max_years = int(exp_match.group(2)) if (exp_match and exp_match.group(2)) else None

        # Notice period
        np_match = re.search(r"(\d+)\s*(?:days?|day)\s*notice", text_lower)
        notice_days = int(np_match.group(1)) if np_match else 30

        # Skills extraction
        found_skills = [s for s in COMMON_SKILLS if s.lower() in text_lower]
        if not found_skills:
            found_skills = ["Python", "FastAPI", "SQL"]

        must_have = [
            SkillRequirement(
                name=s,
                normalized_name=s.lower(),
                description=f"Core proficiency in {s}",
                importance="mandatory",
                evidence=f"Extracted from JD text mentioning {s}",
                is_mandatory=True,
            )
            for s in found_skills[:4]
        ]
        nice_to_have = [
            SkillRequirement(
                name=s,
                normalized_name=s.lower(),
                description=f"Beneficial knowledge of {s}",
                importance="preferred",
                evidence=f"Extracted from JD text mentioning {s}",
                is_mandatory=False,
            )
            for s in found_skills[4:8]
        ]

        result = JDExtractionResult(
            job_title=job_title,
            department="Engineering",
            seniority_level="Senior" if "senior" in text_lower else "Mid-Level",
            location="Remote" if "remote" in text_lower else "Hybrid",
            employment_type="Full-time",
            summary=text[:300].strip(),
            experience=ExperienceRequirement(
                minimum_years=min_years,
                maximum_years=max_years,
                evidence=f"Requires {min_years}+ years experience",
                is_explicit=True,
            ),
            must_have_skills=must_have,
            nice_to_have_skills=nice_to_have,
            notice_period=NoticePeriodRequirement(
                maximum_days=notice_days,
                original_wording=f"{notice_days} days notice",
                is_explicit=bool(np_match),
            ),
            extraction_warnings=[
                ExtractionWarning(
                    field="provider",
                    message="Extracted via deterministic test provider (MockLLMProvider)",
                    severity="info",
                )
            ],
        )
        return result.model_dump()

    async def extract_resume(
        self,
        prompt: str,
        output_schema: dict[str, Any],
        max_tokens: int,
    ) -> dict[str, Any]:
        """
        Extract structured candidate profile from resume text using
        deterministic heuristic regex parsing.
        """
        text = prompt

        # 1. Email extraction
        email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
        email = email_match.group(0).lower() if email_match else None

        # 2. Phone extraction
        phone_match = re.search(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\+?\d{10,14}", text)
        phone = phone_match.group(0) if phone_match else None

        # 3. Full name extraction
        full_name = None
        for line in text.split("\n")[:10]:
            cleaned = line.strip()
            # Clean common resume header prefixes
            cleaned = re.sub(r"^(?:name\s*:\s*|resume\s*-\s*)", "", cleaned, flags=re.I).strip()
            if cleaned and len(cleaned.split()) in (2, 3, 4) and not any(c in cleaned for c in "@:/\\"):
                # Avoid headers like "Curriculum Vitae" or "Summary"
                if not re.search(r"(curriculum|vitae|resume|profile|summary|contact|experience)", cleaned, re.I):
                    full_name = cleaned
                    break

        if not full_name:
            if email:
                prefix = email.split("@")[0].replace(".", " ").replace("_", " ")
                full_name = prefix.title()
            else:
                full_name = "Candidate Profile"

        # 4. Notice period extraction
        notice_period_days: Optional[int] = None
        np_match = re.search(r"(\d+)\s*(?:days?|day)\s*notice", text, re.I)
        if np_match:
            notice_period_days = int(np_match.group(1))
        elif re.search(r"immediate(?:\s+joiner)?", text, re.I):
            notice_period_days = 0

        # 5. Experience extraction
        total_experience_years: Optional[float] = None
        exp_match = re.search(r"(\d+(?:\.\d+)?)\+?\s*years?(?:\s+of)?\s+experience", text, re.I)
        if exp_match:
            total_experience_years = float(exp_match.group(1))

        # 6. Skills extraction
        text_lower = text.lower()
        skills: List[CandidateSkillItem] = []
        for s in COMMON_SKILLS:
            if re.search(r"\b" + re.escape(s.lower()) + r"\b", text_lower):
                # Locate snippet
                match_pos = text_lower.find(s.lower())
                start = max(0, match_pos - 20)
                end = min(len(text), match_pos + len(s) + 40)
                snippet = text[start:end].replace("\n", " ").strip()
                skills.append(
                    CandidateSkillItem(
                        name=s.lower(),
                        raw_name=s,
                        evidence=f"...{snippet}...",
                    )
                )

        # 7. Employment history extraction
        employments: List[CandidateEmploymentItem] = []
        companies = ["TechCorp", "Acme Systems", "Global Logistics", "Innovatech", "Software Solutions"]
        for c_name in companies:
            if c_name.lower() in text_lower:
                employments.append(
                    CandidateEmploymentItem(
                        company=c_name,
                        job_title="Software Engineer",
                        start_date="2020-01",
                        end_date="Present",
                        is_current=True,
                        description=f"Developed backend services at {c_name}",
                        technologies=[s.name for s in skills[:3]],
                    )
                )

        if not employments and skills:
            employments.append(
                CandidateEmploymentItem(
                    company="Technology Services",
                    job_title="Senior Software Engineer",
                    start_date="2021-01",
                    end_date="2024-01",
                    is_current=True,
                    description="Engineered scalable software solutions.",
                    technologies=[s.name for s in skills[:3]],
                )
            )

        # 8. Education extraction
        educations = [
            CandidateEducationItem(
                institution="University Institute of Technology",
                qualification="Bachelor of Technology",
                field_of_study="Computer Science",
                graduation_year=2019,
            )
        ]

        result = ResumeExtractionResult(
            full_name=full_name,
            email=email,
            phone=phone,
            location="Bangalore, India",
            notice_period_days=notice_period_days or 30,
            total_experience_years=total_experience_years or 5.0,
            skills=skills,
            employment_history=employments,
            education=educations,
            certifications=[],
            warnings=["Extracted via deterministic test provider (MockLLMProvider)."],
            missing_fields=[],
        )
        return result.model_dump()

    async def extract_evidence(
        self,
        prompt: str,
        output_schema: dict[str, Any],
        max_tokens: int,
    ) -> dict[str, Any]:
        """
        Extract criteria evidence citations from candidate resume text using
        deterministic keyword matching.
        """
        text = prompt
        text_lower = text.lower()

        # Try to parse criteria from prompt JSON block
        criteria_list: List[Dict[str, Any]] = []
        criteria_block = re.search(r"SCORECARD CRITERIA:\s*---\s*(\[.*?\])\s*---", text, re.DOTALL)
        if criteria_block:
            import json
            try:
                criteria_list = json.loads(criteria_block.group(1))
            except Exception:
                pass

        if not criteria_list:
            # Fallback regex search for criteria (handles both JSON and plaintext formats)
            for m in re.finditer(
                r"(?:Criterion\s+ID|id|criterion_id)[\"':\s]+([a-zA-Z0-9_-]+)[\s\S]*?(?:Name|name)[\"':\s]+([^\n,\"]+)",
                text,
                re.I,
            ):
                criteria_list.append({"id": m.group(1).strip(), "name": m.group(2).strip()})

        # If still empty, create at least one synthetic criterion for test inputs
        if not criteria_list:
            cid_match = re.search(r"([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})", text)
            if cid_match:
                criteria_list.append({"id": cid_match.group(1), "name": "General Requirement"})

        # Extract the resume text section from prompt to avoid matching criteria definitions
        resume_block = re.search(r"EXTRACTED RESUME TEXT:\s*---\s*([\s\S]*?)\s*---", text)
        if resume_block:
            resume_content = resume_block.group(1)
        else:
            # Fallback if raw text was passed (e.g. in standalone tests)
            resume_content = text
            # Strip prompt header if present
            if "Candidate Resume Text:" in resume_content:
                resume_content = resume_content.split("Candidate Resume Text:", 1)[1]
        resume_content_lower = resume_content.lower()

        evidence_items: List[CriterionEvidenceItem] = []

        for crit in criteria_list:
            cid = str(crit.get("id") or crit.get("criterion_id") or "c-000")
            cname = str(crit.get("name") or crit.get("criterion_name") or "Skill")
            ctype = str(crit.get("criterion_type") or "").lower()
            cname_lower = cname.lower()

            matched_kw: Optional[str] = None

            if ctype == "experience" or "experience" in cname_lower or "years" in cname_lower:
                for cand_kw in ["experience", "years", "year"]:
                    if cand_kw in resume_content_lower:
                        matched_kw = cand_kw
                        break
            elif ctype == "notice_period" or "notice" in cname_lower:
                for cand_kw in ["notice", "immediate"]:
                    if cand_kw in resume_content_lower:
                        matched_kw = cand_kw
                        break
            elif ctype == "location" or "location" in cname_lower:
                loc_val = crit.get("config", {}).get("location") if isinstance(crit.get("config"), dict) else None
                loc_words = [loc_val.lower()] if loc_val else [w for w in cname_lower.split() if w not in ("location", "remote", "hybrid", "in")]
                for lw in loc_words:
                    if lw in resume_content_lower:
                        matched_kw = lw
                        break
            else:
                # Skill matching: check full skill name first, then significant tokens
                if cname_lower in resume_content_lower:
                    matched_kw = cname_lower
                else:
                    for token in cname_lower.split():
                        if len(token) >= 3 and token not in ("and", "with", "the", "for", "skills", "proficient") and token in resume_content_lower:
                            matched_kw = token
                            break

            if matched_kw and matched_kw in resume_content_lower:
                # Find exact excerpt in resume text
                idx = resume_content_lower.find(matched_kw)
                start = max(0, idx - 20)
                end = min(len(resume_content), idx + len(matched_kw) + 30)
                excerpt = resume_content[start:end].replace("\n", " ").strip()
                evidence_items.append(
                    CriterionEvidenceItem(
                        criterion_id=cid,
                        criterion_name=cname,
                        match_status="MATCHED",
                        evidence_text=excerpt,
                        source_reference="Resume experience section",
                        confidence=0.92,
                        explanation=f"Demonstrated verified competency in {cname}.",
                    )
                )
            else:
                evidence_items.append(
                    CriterionEvidenceItem(
                        criterion_id=cid,
                        criterion_name=cname,
                        match_status="NOT_MATCHED",
                        evidence_text=None,
                        source_reference=None,
                        confidence=0.0,
                        explanation=f"No explicit mention of {cname} found in resume.",
                    )
                )

        result = CandidateEvidenceExtractionResult(
            criteria_evidence=evidence_items,
            notes="Extracted via deterministic test provider (MockLLMProvider).",
        )
        return result.model_dump()
