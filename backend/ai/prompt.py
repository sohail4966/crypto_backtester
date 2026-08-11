"""
System prompt construction for NL → DSL (JSON Schema in prompt — D-114).
"""

from __future__ import annotations

import json
from typing import Any

from dsl.json_schema_export import strategy_json_schema
from indicators.registry import INDICATORS

_FEW_SHOT_EXAMPLES: list[dict[str, Any]] = [
    {
        "nl": (
            "buy when the daily RSI is oversold and price is above the 200 SMA, "
            "sell when RSI goes overbought"
        ),
        "response": {
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
        },
    },
    {
        "nl": "enter long when RSI crosses above 50",
        "response": {
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
        },
    },
]


def available_indicator_names() -> list[str]:
    """Return sorted registry indicator keys for prompt context."""
    return sorted(INDICATORS.keys())


def build_system_prompt(*, schema: dict[str, Any] | None = None) -> str:
    """
    Build the system prompt with Phase 9 JSON Schema and few-shot examples.

    Args:
        schema: Optional precomputed schema; defaults to ``strategy_json_schema()``.

    Returns:
        System prompt string for the LLM provider.
    """
    schema_doc = schema if schema is not None else strategy_json_schema()
    indicators = ", ".join(available_indicator_names())
    examples_block = "\n\n".join(
        f"Example NL:\n{ex['nl']}\nExample JSON response:\n"
        f"{json.dumps(ex['response'], indent=2)}"
        for ex in _FEW_SHOT_EXAMPLES
    )
    return f"""You are a trading strategy translator for a crypto backtester.
Convert the user's plain-English strategy into a JSON response envelope.

Rules:
1. Emit ONLY valid JSON — no markdown fences, no commentary.
2. The strategy object MUST conform to the Trading DSL JSON Schema below.
3. Prefer indicator names from this allow-list: {indicators}.
4. Generate data (JSON) only — never code, never shell commands.
5. If the request is ambiguous (missing thresholds, timeframes, or conflicting rules),
   do NOT invent defaults. Respond with status "needs_clarification" and questions.
6. Response envelope:
   - Success: {{"status":"ok","strategy":{{...}}}}
   - Ambiguous: {{"status":"needs_clarification","questions":[
        {{"id":"...","prompt":"...","options":["..."]}}
     ]}}

Trading DSL JSON Schema:
{json.dumps(schema_doc, indent=2)}

{examples_block}
"""


def build_user_prompt(
    text: str,
    *,
    prior_answers: dict[str, str] | None = None,
    prior_questions: list[dict[str, Any]] | None = None,
) -> str:
    """
    Build the user message, optionally including clarification Q&A context.

    Args:
        text: Original natural language strategy description.
        prior_answers: Map of question id → user answer.
        prior_questions: Questions previously asked (for context).

    Returns:
        User prompt string.
    """
    parts = [f"Strategy description:\n{text.strip()}"]
    if prior_questions and prior_answers:
        qa_lines: list[str] = []
        for q in prior_questions:
            qid = str(q.get("id", ""))
            if qid in prior_answers:
                qa_lines.append(f"- {q.get('prompt', qid)} → {prior_answers[qid]}")
        if qa_lines:
            parts.append("Clarifications from the user:\n" + "\n".join(qa_lines))
    parts.append("Respond with the JSON envelope only.")
    return "\n\n".join(parts)
