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
