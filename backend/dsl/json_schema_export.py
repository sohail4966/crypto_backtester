"""
Export JSON Schema for LLM prompting / external validators.
"""

from __future__ import annotations

from typing import Any

from dsl.schema import StrategyModel


def strategy_json_schema() -> dict[str, Any]:
    """
    Return the JSON Schema for ``StrategyModel``.

    Suitable for injection into LLM system prompts (Phase 10).
    """
    return StrategyModel.model_json_schema()
