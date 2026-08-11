"""
Tests for DSL semantic validation edge cases.
"""

from __future__ import annotations

import pytest

from dsl import validate_strategy
from exceptions import InvalidSignalError


def test_not_requires_exactly_one_child() -> None:
    with pytest.raises(InvalidSignalError, match="NOT"):
        validate_strategy(
            {
                "entry": {
                    "op": "NOT",
                    "conditions": [
                        {"indicator": "RSI", "op": "<", "value": 30},
                        {"indicator": "RSI", "op": ">", "value": 70},
                    ],
                },
                "exit": {"indicator": "RSI", "op": ">", "value": 70},
            }
        )


def test_sequence_requires_within_bars() -> None:
    with pytest.raises(InvalidSignalError, match="within_bars"):
        validate_strategy(
            {
                "entry": {
                    "op": "SEQUENCE",
                    "conditions": [
                        {"indicator": "RSI", "op": "<", "value": 30},
                        {"indicator": "RSI", "op": ">", "value": 50},
                    ],
                },
                "exit": {"indicator": "RSI", "op": ">", "value": 70},
            }
        )


def test_legacy_all_still_validates() -> None:
    model = validate_strategy(
        {
            "entry": {
                "all": [
                    {"indicator": "RSI", "params": {"period": 14}, "op": "<", "value": 30},
                    {"indicator": "ADX", "params": {"period": 14}, "op": ">", "value": 20},
                ]
            },
            "exit": {"indicator": "RSI", "params": {"period": 14}, "op": ">", "value": 70},
        }
    )
    assert model.entry is not None
    assert model.entry.all is not None


def test_ref_lookback_validates() -> None:
    model = validate_strategy(
        {
            "entry": {
                "field": "close",
                "op": ">",
                "ref": {"field": "close", "bars_ago": 5},
            },
            "exit": {"indicator": "RSI", "params": {"period": 14}, "op": ">", "value": 70},
        }
    )
    assert model.entry is not None
    assert model.entry.ref is not None
    assert model.entry.ref.bars_ago == 5


def test_negative_bars_ago_rejected() -> None:
    with pytest.raises(InvalidSignalError, match="bars_ago"):
        validate_strategy(
            {
                "entry": {
                    "field": "close",
                    "op": ">",
                    "ref": {"field": "close", "bars_ago": -1},
                },
                "exit": {"indicator": "RSI", "op": ">", "value": 70},
            }
        )
