"""
Provider factory for Phase 10 AI (pluggable LLM — D-112).
"""

from __future__ import annotations

import os

from ai.providers.base import LLMProvider
from ai.providers.mock import MockLLMProvider
from ai.providers.openai_compat import OpenAICompatProvider


def get_provider(
    *,
    provider_name: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    timeout_sec: float | None = None,
) -> LLMProvider:
    """
    Resolve the configured LLM provider.

    Selection:
    - Explicit ``provider_name`` / ``AI_LLM_PROVIDER`` wins.
    - Else ``openai_compat`` when an API key is present, otherwise ``mock``.

    Args:
        provider_name: Optional override (``mock`` | ``openai_compat``).
        api_key: Optional API key override.
        base_url: Optional base URL override.
        model: Optional model override.
        timeout_sec: Optional timeout override.

    Returns:
        Concrete ``LLMProvider`` instance.
    """
    name = (provider_name or os.environ.get("AI_LLM_PROVIDER") or "").strip().lower()
    key = api_key if api_key is not None else os.environ.get("AI_LLM_API_KEY", "")
    if not name:
        name = "openai_compat" if key else "mock"

    if name == "mock":
        return MockLLMProvider()
    if name == "openai_compat":
        return OpenAICompatProvider(
            api_key=key or "",
            base_url=base_url
            or os.environ.get("AI_LLM_BASE_URL", "https://api.openai.com/v1"),
            model=model or os.environ.get("AI_LLM_MODEL", "gpt-4o-mini"),
            timeout_sec=timeout_sec
            if timeout_sec is not None
            else float(os.environ.get("AI_LLM_TIMEOUT_SEC", "60")),
        )
    raise ValueError(f"Unknown AI_LLM_PROVIDER: {name}")


__all__ = [
    "LLMProvider",
    "MockLLMProvider",
    "OpenAICompatProvider",
    "get_provider",
]
