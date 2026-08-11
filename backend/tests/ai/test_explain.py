"""Unit tests for template strategy explanation."""

from __future__ import annotations

from ai.explain import explain_strategy


def test_explain_nested_and() -> None:
    """AND groups are joined with 'and'."""
    text = explain_strategy(
        {
            "schema_version": "1",
            "entry_trigger": "edge",
            "entry": {
                "op": "AND",
                "conditions": [
                    {"indicator": "RSI", "params": {"period": 14}, "op": "<", "value": 30},
                    {
                        "field": "close",
                        "op": ">",
                        "compare": {"indicator": "SMA", "params": {"period": 200}},
                    },
                ],
            },
            "exit": {"indicator": "RSI", "params": {"period": 14}, "op": ">", "value": 70},
        }
    )
    assert "schema v1" in text
    assert "RSI" in text
    assert "and" in text
    assert "Exit when" in text
    assert "edge" in text
