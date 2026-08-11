"""
Template-based DSL → English explanation (no LLM required).
"""

from __future__ import annotations

from typing import Any


def explain_strategy(strategy: dict[str, Any]) -> str:
    """
    Explain a validated strategy dict in plain English.

    Args:
        strategy: Strategy mapping (entry / exit / optional schema_version).

    Returns:
        Human-readable multi-sentence explanation.
    """
    parts: list[str] = []
    version = strategy.get("schema_version", "1")
    parts.append(f"Strategy (schema v{version}).")

    entry = strategy.get("entry")
    if entry is not None:
        parts.append("Enter when " + _explain_condition(entry) + ".")

    exit_cond = strategy.get("exit")
    if exit_cond is not None:
        parts.append("Exit when " + _explain_condition(exit_cond) + ".")

    trigger = strategy.get("entry_trigger")
    if trigger:
        parts.append(f"Entry trigger mode: {trigger}.")

    return " ".join(parts)


def _explain_condition(node: Any) -> str:
    """Recursively explain a condition tree node."""
    if not isinstance(node, dict):
        return str(node)

    if "all" in node and isinstance(node["all"], list):
        return " and ".join(_explain_condition(c) for c in node["all"])

    op = node.get("op")
    if op in {"AND", "OR"} and isinstance(node.get("conditions"), list):
        joiner = " and " if op == "AND" else " or "
        return joiner.join(_explain_condition(c) for c in node["conditions"])
    if op == "NOT" and isinstance(node.get("conditions"), list) and node["conditions"]:
        return "not (" + _explain_condition(node["conditions"][0]) + ")"
    if op == "SEQUENCE" and isinstance(node.get("conditions"), list):
        within = node.get("within_bars", "?")
        steps = " then ".join(_explain_condition(c) for c in node["conditions"])
        return f"sequence within {within} bars: {steps}"

    if "smc" in node:
        side = node.get("side")
        side_bit = f" ({side})" if side else ""
        return f"SMC {node['smc']}{side_bit}"

    if "pattern" in node:
        return f"pattern {node['pattern']}"

    if "indicator" in node:
        name = str(node["indicator"])
        params = node.get("params") or {}
        param_bit = (
            "(" + ", ".join(f"{k}={v}" for k, v in params.items()) + ")" if params else ""
        )
        cmp_op = node.get("op", "?")
        rhs = _explain_rhs(node)
        tf = node.get("timeframe")
        tf_bit = f" on {tf}" if tf else ""
        return f"{name}{param_bit}{tf_bit} {cmp_op} {rhs}"

    if "field" in node:
        field = str(node["field"])
        cmp_op = node.get("op", "?")
        rhs = _explain_rhs(node)
        bars = node.get("bars_ago")
        left = f"{field}[{bars}]" if bars is not None else field
        return f"{left} {cmp_op} {rhs}"

    return "complex condition"


def _explain_rhs(node: dict[str, Any]) -> str:
    """Format comparison right-hand side."""
    if "value" in node:
        return str(node["value"])
    if "ref" in node and isinstance(node["ref"], dict):
        ref = node["ref"]
        if "field" in ref:
            bars = ref.get("bars_ago")
            base = str(ref["field"])
            return f"{base}[{bars}]" if bars is not None else base
        if "indicator" in ref:
            return str(ref["indicator"])
        return "ref"
    if "compare" in node:
        cmp = node["compare"]
        if isinstance(cmp, str):
            return cmp
        if isinstance(cmp, dict) and "indicator" in cmp:
            params = cmp.get("params") or {}
            param_bit = (
                "(" + ", ".join(f"{k}={v}" for k, v in params.items()) + ")"
                if params
                else ""
            )
            return f"{cmp['indicator']}{param_bit}"
    return "?"
