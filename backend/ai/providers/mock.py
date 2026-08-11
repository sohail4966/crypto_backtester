"""
Offline / fixture LLM provider for tests and local default (D-112).
"""

from __future__ import annotations

import json
import re
from typing import Any


_VALID_RSI_SMA: dict[str, Any] = {
    "status": "ok",
    "strategy": {
        "schema_version": "1",
        "entry_trigger": "edge",
        "entry": {
            "op": "AND",
            "conditions": [
                {
                    "indicator": "RSI",
                    "params": {"period": 14},
                    "timeframe": "1d",
                    "op": "<",
                    "value": 30,
                },
                {
                    "field": "close",
                    "op": ">",
                    "compare": {"indicator": "SMA", "params": {"period": 200}},
                },
            ],
        },
        "exit": {
            "indicator": "RSI",
            "params": {"period": 14},
            "op": ">",
            "value": 70,
        },
    },
}

_VALID_SIMPLE_RSI: dict[str, Any] = {
    "status": "ok",
    "strategy": {
        "schema_version": "1",
        "entry_trigger": "edge",
        "entry": {
            "indicator": "RSI",
            "params": {"period": 14},
            "op": ">",
            "value": 50,
        },
        "exit": {
            "indicator": "RSI",
            "params": {"period": 14},
            "op": "<",
            "value": 50,
        },
    },
}

_CLARIFY_RSI_LOW: dict[str, Any] = {
    "status": "needs_clarification",
    "questions": [
        {
            "id": "rsi_oversold",
            "prompt": "What RSI level should count as oversold / low?",
            "options": ["30", "25", "20"],
        },
        {
            "id": "rsi_period",
            "prompt": "Which RSI period should we use?",
            "options": ["14", "7", "21"],
        },
    ],
}

_INVALID_STRATEGY: dict[str, Any] = {
    "status": "ok",
    "strategy": {
        "schema_version": "1",
        "entry": {"not_a_valid_leaf": True},
    },
}


class MockLLMProvider:
    """Deterministic fixture provider — no network."""

    name = "mock"

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """
        Return a fixture JSON envelope based on user prompt keywords.

        Args:
            system_prompt: Ignored (schema already known to fixtures).
            user_prompt: Inspected for fixture triggers and clarifications.

        Returns:
            JSON string envelope.
        """
        _ = system_prompt
        text = user_prompt.lower()

        if "invalid:" in text:
            return json.dumps(_INVALID_STRATEGY)

        # After clarifications for RSI-low style prompts, emit a strategy.
        if "clarifications from the user:" in text:
            answers = _parse_answers(user_prompt)
            threshold = _as_float(answers.get("rsi_oversold"), 30.0)
            period = int(_as_float(answers.get("rsi_period"), 14.0))
            payload = {
                "status": "ok",
                "strategy": {
                    "schema_version": "1",
                    "entry_trigger": "edge",
                    "entry": {
                        "indicator": "RSI",
                        "params": {"period": period},
                        "op": "<",
                        "value": threshold,
                    },
                    "exit": {
                        "indicator": "RSI",
                        "params": {"period": period},
                        "op": ">",
                        "value": 70,
                    },
                },
            }
            return json.dumps(payload)

        if "ambiguous:" in text or re.search(r"rsi\s+is\s+low", text):
            return json.dumps(_CLARIFY_RSI_LOW)

        if "sma" in text and "rsi" in text:
            return json.dumps(_VALID_RSI_SMA)

        return json.dumps(_VALID_SIMPLE_RSI)


def _parse_answers(user_prompt: str) -> dict[str, str]:
    """Extract `question → answer` lines from the clarification block."""
    answers: dict[str, str] = {}
    in_block = False
    for line in user_prompt.splitlines():
        if line.strip().lower().startswith("clarifications from the user:"):
            in_block = True
            continue
        if in_block:
            if line.strip().startswith("Respond with"):
                break
            m = re.match(r"-\s*(.+?)\s*→\s*(.+)\s*$", line.strip())
            if not m:
                continue
            prompt_text = m.group(1).lower()
            value = m.group(2).strip()
            if "oversold" in prompt_text or "low" in prompt_text:
                answers["rsi_oversold"] = value
            elif "period" in prompt_text:
                answers["rsi_period"] = value
    return answers


def _as_float(raw: str | None, default: float) -> float:
    """Parse a float answer with fallback."""
    if raw is None:
        return default
    try:
        return float(raw.strip())
    except ValueError:
        return default
