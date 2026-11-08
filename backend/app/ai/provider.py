"""
LLM Provider abstraction protocol.

All AI calls go through this interface. Concrete implementations
are loaded by provider_factory.py based on configuration.
No service module imports a concrete provider directly.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


class LLMExtractionError(Exception):
    """Raised when an LLM provider call fails for any reason."""

    def __init__(self, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class LLMProviderUnavailableError(LLMExtractionError):
    """Provider is not configured or not reachable."""

    def __init__(self, message: str = "AI provider is not available") -> None:
        super().__init__(message, retryable=False)


@runtime_checkable
class LLMProvider(Protocol):
    """
    Abstract interface for all LLM provider implementations.
    Switching providers requires only a configuration change.
    """

    async def extract_jd(
        self,
        prompt: str,
        output_schema: dict[str, Any],
        max_tokens: int,
    ) -> dict[str, Any]:
        """
        Extract structured requirements from a job description.
        Returns a validated dict matching output_schema.
        Raises LLMExtractionError on failure.
        """
        ...

    async def extract_resume(
        self,
        prompt: str,
        output_schema: dict[str, Any],
        max_tokens: int,
    ) -> dict[str, Any]:
        """
        Extract structured candidate profile from a resume.
        Returns a validated dict matching output_schema.
        Raises LLMExtractionError on failure.
        """
        ...

    async def extract_evidence(
        self,
        prompt: str,
        output_schema: dict[str, Any],
        max_tokens: int,
    ) -> dict[str, Any]:
        """
        Extract structured evidence matching criteria against candidate data.
        Returns a validated dict matching output_schema.
        Raises LLMExtractionError on failure.
        """
        ...
