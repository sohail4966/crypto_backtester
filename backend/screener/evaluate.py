"""
Collect timeframes referenced by ``timeframe`` keys in a condition tree.
"""

from __future__ import annotations

from typing import Any


def collect_condition_timeframes(condition: dict[str, Any]) -> set[str]:
    """
    Walk a condition tree and return all leaf ``timeframe`` values.

    Supports Phase 8 ``all`` / ``any`` / ``not`` and Phase 9 ``conditions`` groups.
    """
    found: set[str] = set()
    if "all" in condition:
        for leg in condition["all"]:
            found |= collect_condition_timeframes(leg)
        return found
    if "any" in condition:
        for leg in condition["any"]:
            found |= collect_condition_timeframes(leg)
        return found
    if "not" in condition and isinstance(condition["not"], dict):
        return collect_condition_timeframes(condition["not"])
    if "conditions" in condition and isinstance(condition["conditions"], list):
        for leg in condition["conditions"]:
            found |= collect_condition_timeframes(leg)
        return found
    tf = condition.get("timeframe")
    if isinstance(tf, str) and tf:
        found.add(tf)
    return found
