"""
OpenAI concrete implementation of LLMProvider.

Uses the openai Python SDK with JSON mode to enforce structured output.
Implements the retry/timeout policy from the architecture spec.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from app.ai.provider import LLMExtractionError, LLMProviderUnavailableError
from app.core.config import Settings

logger = logging.getLogger("shortlistai.ai.openai")


class OpenAIProvider:
    """
    Concrete OpenAI LLM provider implementation.

    Retryable errors: network errors, timeouts, rate limits (429).
    Non-retryable: auth errors (401), malformed JSON, schema failures.
    """

    def __init__(self, config: Settings) -> None:
        self._config = config
        self._client = None
        self._model = config.AI_MODEL
        self._timeout = config.AI_REQUEST_TIMEOUT
        self._max_retries = config.AI_MAX_RETRIES

        effective_key = config.get_effective_ai_api_key()
        if not effective_key:
            logger.warning(
                "AI_API_KEY is not configured. OpenAI provider will be unavailable."
            )
            return

        try:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                api_key=effective_key,
                timeout=float(config.AI_REQUEST_TIMEOUT),
                max_retries=0,  # We handle retries ourselves
            )
        except ImportError:
            logger.warning("openai package not installed. AI features will be unavailable.")

    def _is_available(self) -> bool:
        return self._client is not None and bool(self._config.get_effective_ai_api_key())

    async def extract_jd(
        self,
        prompt: str,
        output_schema: dict[str, Any],
        max_tokens: int,
    ) -> dict[str, Any]:
        if not self._is_available():
            raise LLMProviderUnavailableError(
                "OpenAI provider is not configured. Set AI_API_KEY in environment."
            )

        from app.ai.prompts import JD_EXTRACTION_SYSTEM_PROMPT
        from openai import APIConnectionError, APIStatusError, RateLimitError

        last_error: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                t0 = time.monotonic()
                response = await self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": JD_EXTRACTION_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                    max_tokens=max_tokens,
                    temperature=0,
                )
                latency_ms = int((time.monotonic() - t0) * 1000)

                raw = response.choices[0].message.content
                if not raw:
                    raise LLMExtractionError("Empty response from AI provider", retryable=False)

                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError as e:
                    raise LLMExtractionError(
                        f"Malformed JSON from AI provider: {e}", retryable=False
                    )

                logger.info(
                    "AI JD extraction complete",
                    extra={
                        "provider": "openai",
                        "model": self._model,
                        "attempt": attempt,
                        "latency_ms": latency_ms,
                        "input_tokens": response.usage.prompt_tokens if response.usage else None,
                        "output_tokens": response.usage.completion_tokens if response.usage else None,
                    },
                )
                return parsed

            except LLMExtractionError:
                raise  # non-retryable, propagate immediately

            except RateLimitError as e:
                err_str = str(e).lower()
                if "insufficient_quota" in err_str or "credit_balance_exhausted" in err_str or "billing" in err_str:
                    logger.warning("AI provider quota exhausted: %s", e)
                    raise LLMExtractionError(
                        "AI provider quota exhausted. Check API credits.",
                        retryable=False,
                    )
                last_error = LLMExtractionError(
                    f"AI provider rate limit reached: {e}", retryable=True
                )
                logger.warning(f"OpenAI rate limit on attempt {attempt}/{self._max_retries}")

            except APIStatusError as e:
                if e.status_code == 401:
                    raise LLMExtractionError(
                        "AI provider authentication failed. Check AI_API_KEY.", retryable=False
                    )
                last_error = LLMExtractionError(
                    f"AI provider API error {e.status_code}: {e.message}", retryable=True
                )
                logger.warning(f"OpenAI API error {e.status_code} on attempt {attempt}")

            except (APIConnectionError, asyncio.TimeoutError, TimeoutError) as e:
                last_error = LLMExtractionError(
                    f"AI provider connection error: {e}", retryable=True
                )
                logger.warning(f"OpenAI connection error on attempt {attempt}: {e}")

            except Exception as e:
                raise LLMExtractionError(f"Unexpected AI provider error: {e}", retryable=False)

            if attempt < self._max_retries:
                wait = 2 ** (attempt - 1)  # 1s, 2s, 4s
                await asyncio.sleep(wait)

        raise last_error or LLMExtractionError("AI extraction failed after retries", retryable=False)
