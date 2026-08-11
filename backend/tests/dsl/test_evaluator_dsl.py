"""
End-to-end DSL evaluation tests (AND/OR/NOT, lookback, multi-TF, pattern).
"""

from __future__ import annotations

import pandas as pd

from signals.evaluator import evaluate_signals


def _daily(n: int = 40) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ts": pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC"),
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": [100 + (i % 7) for i in range(n)],
            "volume": 1000.0,
        }
    )


def test_and_or_not_evaluation() -> None:
    candles = _daily()
    strategy = {
        "schema_version": "1",
        "entry_trigger": "level",
        "entry": {
            "op": "AND",
            "conditions": [
                {"indicator": "RSI", "params": {"period": 14}, "op": "<", "value": 100},
                {
                    "op": "OR",
                    "conditions": [
                        {"field": "close", "op": ">", "value": 0},
                        {"op": "NOT", "conditions": [{"field": "close", "op": "<", "value": 0}]},
                    ],
                },
            ],
        },
        "exit": {"indicator": "RSI", "params": {"period": 14}, "op": ">", "value": 70},
    }
    entry, exit_ = evaluate_signals(candles, strategy, base_timeframe="1d")
    assert entry.dtype == bool
    assert entry.any()
    assert len(exit_) == len(candles)


def test_bars_ago_lookback() -> None:
    candles = _daily(20)
    # close > close[1] roughly when series rises
    strategy = {
        "schema_version": "1",
        "entry_trigger": "level",
        "entry": {
            "field": "close",
            "op": ">",
            "ref": {"field": "close", "bars_ago": 1},
        },
        "exit": {"field": "close", "op": "<", "value": 0},
    }
    entry, _ = evaluate_signals(candles, strategy, base_timeframe="1d")
    # First bar cannot look back → False
    assert bool(entry.iloc[0]) is False
    assert entry.dtype == bool


def test_cross_indicator_compare_still_works() -> None:
    candles = _daily(50)
    strategy = {
        "schema_version": "1",
        "entry_trigger": "level",
        "entry": {
            "indicator": "EMA",
            "params": {"period": 5},
            "op": ">",
            "compare": {"indicator": "EMA", "params": {"period": 20}},
        },
        "exit": {"indicator": "RSI", "params": {"period": 14}, "op": ">", "value": 70},
    }
    entry, exit_ = evaluate_signals(candles, strategy, base_timeframe="1d")
    assert len(entry) == len(candles)
    assert exit_.dtype == bool


def test_multi_timeframe_condition_aligns() -> None:
    # Hourly base with a daily field condition — resample + look-ahead-safe align.
    n = 72
    candles = pd.DataFrame(
        {
            "ts": pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC"),
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": [100 + (i % 11) for i in range(n)],
            "volume": 1.0,
        }
    )
    strategy = {
        "schema_version": "1",
        "entry_trigger": "level",
        "entry": {
            "field": "close",
            "timeframe": "1d",
            "op": ">",
            "value": 0,
        },
        "exit": {"field": "close", "op": "<", "value": 0},
    }
    entry, _ = evaluate_signals(candles, strategy, base_timeframe="1h")
    assert len(entry) == n
    # With as-of ffill, the first daily open is visible on the first hourly bar.
    assert bool(entry.iloc[0]) is True
    assert bool(entry.iloc[24]) is True


def test_pattern_leaf_evaluates() -> None:
    candles = _daily(30)
    strategy = {
        "schema_version": "1",
        "entry_trigger": "level",
        "entry": {
            "op": "OR",
            "conditions": [
                {"pattern": "doji"},
                {"indicator": "RSI", "params": {"period": 14}, "op": "<", "value": 100},
            ],
        },
        "exit": {"indicator": "RSI", "params": {"period": 14}, "op": ">", "value": 70},
    }
    entry, _ = evaluate_signals(candles, strategy, base_timeframe="1d")
    assert entry.dtype == bool
    assert len(entry) == len(candles)
