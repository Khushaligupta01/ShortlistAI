"""
Prompt templates for JD extraction.
Prompts are kept here so they can be versioned and tested independently.
"""
from __future__ import annotations

PROTECTED_ATTRIBUTES_NOTICE = """
IMPORTANT: Do NOT include any of the following as requirements under any circumstances:
- Age, date of birth, or years of birth
- Gender or sex
- Marital status
- Photograph or physical appearance
- Religion or belief
- Ethnicity, race, or nationality (unless specifically a language requirement for the role)
If the JD mentions any of these, include a warning in extraction_warnings instead.
"""

JD_EXTRACTION_SYSTEM_PROMPT = f"""You are a precise job description parser for a recruitment platform.
Your task is to extract structured requirements from a job description.

RULES:
1. Only extract information EXPLICITLY stated in the job description.
2. Do NOT infer, assume, or fabricate any requirements.
3. If a field is not mentioned, return null for that field.
4. For notice period: if not mentioned, return null for maximum_days (never assume 30 or 60 days).
5. For experience: extract exact numbers if stated; if a range like "5-8 years" is given, use min=5 max=8.
6. Skills: include only skills explicitly named or clearly implied by the role description.
7. Additional requirements: only include education/certifications/domain experience explicitly stated.
8. If the JD contains contradictory information, add an entry to extraction_warnings.
9. Mark is_explicit=true only when the requirement is clearly stated, not implied.
{PROTECTED_ATTRIBUTES_NOTICE}

Return a JSON object matching the provided schema exactly.
"""


def build_jd_extraction_prompt(jd_text: str) -> str:
    return f"""Please extract structured requirements from the following job description.

JOB DESCRIPTION:
---
{jd_text[:8000]}
---

Return a JSON object with the extracted requirements. Use null for any field not explicitly mentioned."""


# ---------------------------------------------------------------------------
# Phase 4: Resume Extraction Prompts
# ---------------------------------------------------------------------------

RESUME_EXTRACTION_SYSTEM_PROMPT = f"""You are a precise, objective resume parser for ShortlistAI recruitment platform.
Your task is to extract factual, structured candidate information strictly from the provided resume text.

ABSOLUTE EXTRACTION RULES:
1. ONLY extract information EXPLICITLY supported by the resume text.
2. Missing information must remain null or empty list. NEVER fabricate or guess missing values.
3. NOTICE PERIOD: Extract notice_period_days ONLY if explicitly stated in numbers or words (e.g. "30 days notice", "immediate joiner" -> 0). If not explicitly stated, return null. Never assume notice period.
4. EMPLOYMENT HISTORY: Extract company, job title, start/end dates, description, and technologies.
5. TOTAL EXPERIENCE: Calculate total experience in years ONLY if verifiable from explicit dates or explicitly stated (e.g. "7 years of experience"). If dates are missing or ambiguous, return null or record a warning in warnings.
6. SKILLS: For each skill, include the normalized skill name, raw name as written in the resume, and a short verbatim evidence excerpt from the resume.
7. EDUCATION: Extract institution, qualification, field of study, and graduation year if stated.
8. NO DEMOGRAPHIC INFERENCE:
   - NEVER infer age from graduation year or employment dates.
   - NEVER infer gender, race, religion, or nationality from names, pronouns, or photos.
   - NEVER use demographic attributes.
9. PRESERVE UNCERTAINTY: If dates conflict or information is ambiguous, preserve the ambiguity and list it in 'warnings'.
10. Missing critical fields (e.g. email, phone, location) should be listed by name in 'missing_fields'.

Return a valid JSON object matching the requested schema.
"""


def build_resume_extraction_prompt(resume_text: str) -> str:
    return f"""Please extract structured candidate information from the following resume text.

RESUME TEXT:
---
{resume_text[:12000]}
---

Return a JSON object containing:
- full_name (string or null)
- email (string or null)
- phone (string or null)
- location (string or null)
- notice_period_days (integer or null - only if explicitly stated)
- total_experience_years (number or null)
- skills: list of objects with [name, raw_name, evidence]
- employment_history: list of objects with [company, job_title, start_date, end_date, is_current, description, technologies]
- education: list of objects with [institution, qualification, field_of_study, graduation_year]
- certifications: list of objects with [name, issuing_organization, year]
- warnings: list of string descriptions for conflicts or ambiguities
- missing_fields: list of field names that were not found in the resume

Do not fabricate any details. Use null for missing values."""


# ---------------------------------------------------------------------------
# Phase 5: Evidence Extraction Prompts
# ---------------------------------------------------------------------------

EVIDENCE_EXTRACTION_SYSTEM_PROMPT = """You are an objective, evidence-grounded candidate evaluation assistant for ShortlistAI.
Your task is to analyze candidate professional data against approved scorecard criteria and extract factual, criterion-level evidence.

EVIDENCE RULES:
1. ONLY extract evidence that is explicitly supported by the candidate's structured profile or resume text.
2. NEVER fabricate quotations or assume candidate capabilities that are not substantiated by the resume.
3. Every MATCHED or PARTIAL status must cite a concise, verbatim or closely-grounded excerpt from the resume in 'evidence_text'.
4. USE THESE EXACT STATUSES:
   - MATCHED: The criterion is clearly and explicitly satisfied with evidence.
   - PARTIAL: Evidence partially satisfies the requirement (e.g. experience slightly lower than min, or related technology).
   - NOT_MATCHED: Evidence explicitly contradicts the requirement or clearly shows requirement is not met.
   - UNKNOWN: The resume completely lacks information to determine whether this criterion is met. NEVER treat missing information as NOT_MATCHED.
   - CONFLICTING: Resume contains mutually contradictory or suspicious information for this criterion.
5. SKILL NORMALIZATION & DISTINCTION:
   - "Spring Boot" and "Spring Framework" are distinct technologies. "Spring" alone does not satisfy "Spring Boot".
   - "Java" and "JavaScript" are completely distinct technologies.
   - "C", "C++", and "C#" are distinct languages.
   - Do not use fuzzy matching to award must-have points.
6. NO DEMOGRAPHIC INFLUENCE:
   - Do NOT evaluate or consider candidate name, gender, age, photo, marital status, or nationality.
   - Only evaluate objective professional qualifications (skills, experience, location, notice period).
7. CONFIDENCE: Provide a numeric confidence (0.0 to 1.0) reflecting the clarity of the evidence.

Return a JSON object containing a "criteria_evidence" list with items matching the requested schema.
"""


def build_evidence_extraction_prompt(
    clean_candidate_profile: dict,
    criteria: list[dict],
    resume_text: str,
) -> str:
    import json
    return f"""Please evaluate the candidate's professional evidence against each of the following scorecard criteria.

SCORECARD CRITERIA:
---
{json.dumps(criteria, indent=2)}
---

CANDIDATE PROFESSIONAL PROFILE:
---
{json.dumps(clean_candidate_profile, indent=2)}
---

EXTRACTED RESUME TEXT:
---
{resume_text[:10000]}
---

For EACH criterion in the scorecard criteria list:
1. Identify criterion_id and criterion_name.
2. Determine match_status: MATCHED, PARTIAL, NOT_MATCHED, UNKNOWN, or CONFLICTING.
3. Cite the exact evidence_text from the resume text or profile. If UNKNOWN, evidence_text should be null.
4. Specify source_reference (e.g., "Employment: Lead Developer at Acme Corp" or "Skills section").
5. Provide confidence score (0.0 to 1.0) and a concise explanation.

Return JSON with "criteria_evidence": [...]"""

