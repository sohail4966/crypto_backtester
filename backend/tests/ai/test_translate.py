"""Unit tests for NL → DSL translation with mock provider."""

from __future__ import annotations

import pytest

from ai.providers.mock import MockLLMProvider
from ai.sessions import ClarificationSessionStore
from ai.translate import AITranslateError, apply_clarification, translate_nl
from ai.types import TranslateNeedsClarification, TranslateOk


@pytest.fixture
def store() -> ClarificationSessionStore:
    """Fresh in-memory session store."""
    return ClarificationSessionStore(ttl_minutes=30)


@pytest.fixture
def provider() -> MockLLMProvider:
    """Offline mock LLM."""
    return MockLLMProvider()


def test_translate_valid_strategy(provider: MockLLMProvider, store: ClarificationSessionStore) -> None:
    """Known RSI+SMA phrasing yields a validated strategy."""
    outcome = translate_nl(
        "buy when daily RSI is oversold and price above 200 SMA",
        provider=provider,
        store=store,
    )
    assert isinstance(outcome, TranslateOk)
    assert outcome.strategy["schema_version"] == "1"
    assert "entry" in outcome.strategy
    assert "RSI" in outcome.explanation


def test_translate_ambiguous_asks_clarification(
    provider: MockLLMProvider,
    store: ClarificationSessionStore,
) -> None:
    """Vague RSI-low phrasing returns clarification questions."""
    outcome = translate_nl("buy when RSI is low", provider=provider, store=store)
    assert isinstance(outcome, TranslateNeedsClarification)
    assert outcome.session_id
    assert any(q.id == "rsi_oversold" for q in outcome.questions)


def test_clarify_completes_translation(
    provider: MockLLMProvider,
    store: ClarificationSessionStore,
) -> None:
    """Answering clarification questions produces a validated strategy."""
    first = translate_nl("buy when RSI is low", provider=provider, store=store)
    assert isinstance(first, TranslateNeedsClarification)
    second = apply_clarification(
        first.session_id,
        {"rsi_oversold": "25", "rsi_period": "14"},
        provider=provider,
        store=store,
    )
    assert isinstance(second, TranslateOk)
    entry = second.strategy["entry"]
    assert entry["value"] == 25.0
    assert store.get(first.session_id) is None


def test_invalid_llm_strategy_raises(
    provider: MockLLMProvider,
    store: ClarificationSessionStore,
) -> None:
    """Fixture INVALID: strategy fails validate_strategy."""
    with pytest.raises(AITranslateError) as exc_info:
        translate_nl("INVALID: please break", provider=provider, store=store)
    assert exc_info.value.code == "INVALID_DSL"


def test_empty_text_raises(provider: MockLLMProvider, store: ClarificationSessionStore) -> None:
    """Blank text is rejected before calling the provider."""
    with pytest.raises(AITranslateError) as exc_info:
        translate_nl("   ", provider=provider, store=store)
    assert exc_info.value.code == "EMPTY_TEXT"


def test_unknown_session_raises(provider: MockLLMProvider, store: ClarificationSessionStore) -> None:
    """Clarify on a missing session returns SESSION_NOT_FOUND."""
    caller_supplied = "definitely-not-a-real-session-id-abc123"
    with pytest.raises(AITranslateError) as exc_info:
        apply_clarification(caller_supplied, {"a": "b"}, provider=provider, store=store)
    assert exc_info.value.code == "SESSION_NOT_FOUND"
    # BE-L2-017: caller-supplied id must not leak back through the message.
    assert caller_supplied not in exc_info.value.message
