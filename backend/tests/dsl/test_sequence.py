"""
Tests for SEQUENCE condition evaluation.
"""

from __future__ import annotations

import pandas as pd

from signals.evaluator import _build_context, _evaluate_condition


def _frame(n: int = 20) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC")
    return pd.DataFrame(
        {
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "volume": 1.0,
        },
        index=idx,
    )


def test_sequence_a_then_b_within_n_bars() -> None:
    candles = _frame(15)
    ctx = _build_context(candles, base_timeframe="1d", frames=None)

    # Leg A true only on bar 3; leg B true on bars 5 and 12.
    a = {"field": "close", "op": "==", "value": 100.0}  # always true — too loose
    # Use synthetic by injecting via OR of field compares that we control with volume? 
    # Better: use compare against a shifted custom approach — instead build SEQUENCE
    # over indicator thresholds that we control by mutating close.

    close = candles["close"].copy()
    close.iloc[:] = 50.0
    close.iloc[3] = 10.0  # RSI would be hard; use field thresholds with mutated frame
    close.iloc[5] = 90.0
    close.iloc[12] = 90.0
    candles = candles.copy()
    candles["close"] = close
    ctx = _build_context(candles, base_timeframe="1d", frames=None)

    condition = {
        "op": "SEQUENCE",
        "within_bars": 5,
        "conditions": [
            {"field": "close", "op": "<", "value": 20},
            {"field": "close", "op": ">", "value": 80},
        ],
    }
    series = _evaluate_condition(ctx, condition)
    # Bar 5: B true, A at 3 within window → True
    assert bool(series.iloc[5]) is True
    # Bar 12: B true, but A at 3 is outside within_bars=5 → False
    assert bool(series.iloc[12]) is False


def test_sequence_requires_order() -> None:
    candles = _frame(10)
    close = pd.Series([50.0] * 10, index=candles.index)
    close.iloc[4] = 90.0  # B first
    close.iloc[6] = 10.0  # A later
    candles = candles.copy()
    candles["close"] = close
    ctx = _build_context(candles, base_timeframe="1d", frames=None)
    condition = {
        "op": "SEQUENCE",
        "within_bars": 5,
        "conditions": [
            {"field": "close", "op": "<", "value": 20},
            {"field": "close", "op": ">", "value": 80},
        ],
    }
    series = _evaluate_condition(ctx, condition)
    # No bar where B is true after A
    assert not series.any()
