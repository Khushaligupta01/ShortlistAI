"""
JD Extraction Service.

Orchestrates the JD extraction pipeline:
  1. Build prompt
  2. Call LLM provider
  3. Validate raw output against Pydantic schema
  4. Return typed JDExtractionResult

This service never calls the LLM directly — it always uses
the LLMProvider interface, making it testable with a mock provider.
"""
from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from app.ai.provider import LLMExtractionError, LLMProvider
from app.ai.prompts import build_jd_extraction_prompt
from app.ai.schemas import JDExtractionResult, ExtractionWarning
from app.core.config import settings

logger = logging.getLogger("shortlistai.ai.jd_extraction")

# Protected attribute keywords that should never appear as JD requirements
PROTECTED_KEYWORDS = {
    "gender", "sex", "male", "female", "age", "born", "marital",
    "married", "single", "religion", "race", "ethnicity", "nationality",
    "photograph", "photo", "appearance",
}


def _check_for_protected_attributes(jd_text: str) -> list[ExtractionWarning]:
    """Scan JD text for protected attribute mentions and return warnings."""
    warnings = []
    text_lower = jd_text.lower()
    found = [kw for kw in PROTECTED_KEYWORDS if kw in text_lower]
    if found:
        warnings.append(
            ExtractionWarning(
                field="jd_text",
                message=(
                    f"The job description may contain references to protected attributes: "
                    f"{', '.join(found)}. These have been excluded from extraction. "
                    "Please review the JD for compliance."
                ),
                severity="warning",
            )
        )
    return warnings


class JDExtractionService:
    """
    Service for extracting structured requirements from a job description.
    Injected with an LLMProvider — use a mock in tests.
    """

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    async def extract(self, jd_text: str) -> JDExtractionResult:
        """
        Extract structured requirements from a job description.

        Returns a JDExtractionResult — missing fields are null (never fabricated).
        On provider failure, raises LLMExtractionError.
        """
        if not jd_text or not jd_text.strip():
            return JDExtractionResult(
                extraction_warnings=[
                    ExtractionWarning(
                        field="jd_text",
                        message="Job description is empty.",
                        severity="error",
                    )
                ]
            )

        # Pre-flight: check for protected attribute mentions
        pa_warnings = _check_for_protected_attributes(jd_text)

        prompt = build_jd_extraction_prompt(jd_text)

        try:
            raw: dict[str, Any] = await self._provider.extract_jd(
                prompt=prompt,
                output_schema={},  # schema hint — actual validation is Pydantic below
                max_tokens=settings.AI_MAX_OUTPUT_TOKENS,
            )
        except LLMExtractionError:
            raise  # Let caller handle and return appropriate error response

        # Validate raw AI output strictly with Pydantic
        try:
            result = JDExtractionResult.model_validate(raw)
        except ValidationError as e:
            logger.warning("AI output failed schema validation: %s", e)
            raise LLMExtractionError(
                f"AI returned a response that failed validation: {e}",
                retryable=False,
            )

        # Append any protected-attribute warnings
        if pa_warnings:
            result.extraction_warnings = pa_warnings + result.extraction_warnings

        return result
