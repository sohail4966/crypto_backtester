"""Unit tests for LLM provider factory and mock fixtures."""

from __future__ import annotations

import json

import pytest

from ai.providers import get_provider
from ai.providers.mock import MockLLMProvider
from ai.providers.openai_compat import OpenAICompatProvider


def test_get_provider_defaults_to_mock_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """No API key → mock provider."""
    monkeypatch.delenv("AI_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("AI_LLM_API_KEY", raising=False)
    provider = get_provider()
    assert isinstance(provider, MockLLMProvider)
    assert provider.name == "mock"


def test_get_provider_openai_when_key_set(monkeypatch: pytest.MonkeyPatch) -> None:
    """API key present → openai_compat unless overridden."""
    monkeypatch.delenv("AI_LLM_PROVIDER", raising=False)
    monkeypatch.setenv("AI_LLM_API_KEY", "sk-test-not-real")
    provider = get_provider()
    assert isinstance(provider, OpenAICompatProvider)


def test_explicit_mock_overrides_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """AI_LLM_PROVIDER=mock wins even with a key."""
    monkeypatch.setenv("AI_LLM_PROVIDER", "mock")
    monkeypatch.setenv("AI_LLM_API_KEY", "sk-test-not-real")
    provider = get_provider()
    assert isinstance(provider, MockLLMProvider)


def test_mock_returns_json_envelope() -> None:
    """Mock complete() returns parseable JSON."""
    raw = MockLLMProvider().complete("sys", "buy when RSI crosses 50")
    data = json.loads(raw)
    assert data["status"] == "ok"
    assert "strategy" in data
