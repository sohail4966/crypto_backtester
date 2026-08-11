"""
Tests for DSL pydantic schema and JSON Schema export.
"""

from __future__ import annotations

from dsl import SCHEMA_VERSION, strategy_json_schema, validate_strategy
from exceptions import InvalidSignalError
import pytest


def test_schema_version_constant() -> None:
    assert SCHEMA_VERSION == "1"


def test_strategy_json_schema_has_schema_version() -> None:
    schema = strategy_json_schema()
    assert "properties" in schema
    assert "schema_version" in schema["properties"]


def test_validate_nested_and_or_not() -> None:
    model = validate_strategy(
        {
            "schema_version": "1",
            "entry": {
                "op": "AND",
                "conditions": [
                    {"indicator": "RSI", "params": {"period": 14}, "op": "<", "value": 30},
                    {
                        "op": "OR",
                        "conditions": [
                            {"field": "close", "op": ">", "value": 100},
                            {"op": "NOT", "conditions": [{"pattern": "bearish_engulfing"}]},
                        ],
                    },
                ],
            },
            "exit": {"indicator": "RSI", "params": {"period": 14}, "op": ">", "value": 70},
        }
    )
    assert model.schema_version == "1"
    assert model.entry is not None
    assert model.entry.op == "AND"


def test_validate_rejects_unknown_schema_version() -> None:
    with pytest.raises(InvalidSignalError, match="schema_version"):
        validate_strategy(
            {
                "schema_version": "99",
                "entry": {"indicator": "RSI", "op": "<", "value": 30},
                "exit": {"indicator": "RSI", "op": ">", "value": 70},
            }
        )


def test_validate_defaults_missing_schema_version() -> None:
    model = validate_strategy(
        {
            "entry": {"indicator": "RSI", "params": {"period": 14}, "op": "<", "value": 30},
            "exit": {"indicator": "RSI", "params": {"period": 14}, "op": ">", "value": 70},
        }
    )
    assert model.schema_version == "1"
