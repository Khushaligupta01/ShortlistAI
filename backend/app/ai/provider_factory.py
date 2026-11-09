"""
Factory that loads the configured LLM provider.
Provider selection is driven by the AI_PROVIDER environment variable / settings.
"""
from __future__ import annotations

import logging
from typing import Union

from app.ai.provider import LLMProvider
from app.core.config import Settings

logger = logging.getLogger("shortlistai.ai.factory")


def get_llm_provider(config: Union[Settings, str]) -> LLMProvider:
    """
    Instantiate and return the configured LLMProvider.

    Supported providers:
      - 'openai': Production LLM provider requiring OPENAI_API_KEY.
      - 'mock' / 'fallback' / 'test': Deterministic rule-based provider for automated
        testing and offline development. Strictly rejected in production.
    """
    if isinstance(config, str):
        provider_name = config.lower().strip()
        from app.core.config import settings
        config_obj = settings
    else:
        provider_name = config.AI_PROVIDER.lower().strip()
        config_obj = config

    if provider_name == "openai":
        from app.ai.openai_provider import OpenAIProvider
        return OpenAIProvider(config_obj)  # type: ignore[return-value]

    if provider_name in ("mock", "fallback", "test"):
        if config_obj.APP_ENV == "production":
            raise ValueError(
                f"AI_PROVIDER '{provider_name}' is not permitted in production. "
                "Production requires a valid production provider such as 'openai' with a valid API key."
            )
        from app.ai.mock_provider import MockLLMProvider
        return MockLLMProvider(config_obj)

    raise ValueError(
        f"Unknown AI_PROVIDER '{provider_name}'. "
        "Supported: 'openai' (production) or 'mock'/'fallback' (development and automated testing)."
    )


# Module-level singleton — created once on demand, not per request
_provider: LLMProvider | None = None


def get_provider() -> LLMProvider:
    """Return the module-level provider singleton."""
    global _provider
    if _provider is None:
        from app.core.config import settings
        _provider = get_llm_provider(settings)
    return _provider


def reset_provider() -> None:
    """Reset the module-level provider singleton (useful for test isolation)."""
    global _provider
    _provider = None
