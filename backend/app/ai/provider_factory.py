"""
Factory that loads the configured LLM provider at startup.
Provider selection is purely driven by AI_PROVIDER env var.
"""
from __future__ import annotations

from app.ai.provider import LLMProvider
from app.core.config import Settings


def get_llm_provider(config: Settings) -> LLMProvider:
    provider_name = config.AI_PROVIDER.lower()

    if provider_name == "openai":
        from app.ai.openai_provider import OpenAIProvider
        return OpenAIProvider(config)  # type: ignore[return-value]

    raise ValueError(
        f"Unknown AI_PROVIDER '{provider_name}'. "
        "Supported: 'openai'. Add a new provider in app/ai/provider_factory.py."
    )


# Module-level singleton — created once at import, not per request
_provider: LLMProvider | None = None


def get_provider() -> LLMProvider:
    """Return the module-level provider singleton."""
    global _provider
    if _provider is None:
        from app.core.config import settings
        _provider = get_llm_provider(settings)
    return _provider
