"""Unit tests for AI prompt construction."""

from __future__ import annotations

from ai.prompt import available_indicator_names, build_system_prompt, build_user_prompt


def test_system_prompt_includes_json_schema_and_envelope() -> None:
    """System prompt embeds schema keys and response envelope rules."""
    prompt = build_system_prompt()
    assert "Trading DSL JSON Schema" in prompt
    assert "schema_version" in prompt
    assert "needs_clarification" in prompt
    assert "RSI" in available_indicator_names()
    assert "RSI" in prompt


def test_user_prompt_includes_clarifications() -> None:
    """Clarification answers are appended for follow-up turns."""
    prompt = build_user_prompt(
        "buy when RSI is low",
        prior_answers={"rsi_oversold": "30"},
        prior_questions=[
            {"id": "rsi_oversold", "prompt": "What RSI level counts as oversold?"}
        ],
    )
    assert "Strategy description" in prompt
    assert "oversold" in prompt
    assert "30" in prompt
