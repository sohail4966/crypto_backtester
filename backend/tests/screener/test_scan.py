"""
Tests for Phase 8 screener library.
"""

from __future__ import annotations

import logging

import pandas as pd
import pytest

from exceptions import InvalidSignalError
from screener.alerts import ConsoleAlertSink
from screener.evaluate import collect_condition_timeframes
from screener.pipeline import run_scan
from screener.scan import scan_symbol_timeframe
from signals.evaluator import apply_entry_trigger, evaluate_condition


def _ohlcv(closes: list[float], *, freq: str = "D", start: str = "2024-01-01") -> pd.DataFrame:
    """Build a minimal OHLCV frame from close prices."""
    ts = pd.date_range(start, periods=len(closes), freq=freq, tz="UTC")
    close = pd.Series(closes, dtype=float)
    return pd.DataFrame(
        {
            "ts": ts,
            "open": close - 1,
            "high": close + 2,
            "low": close - 2,
            "close": close,
            "volume": [1000.0] * len(closes),
        }
    )


def test_any_group_ors_legs() -> None:
    """``any`` fires when at least one leg is true."""
    candles = _ohlcv([100 + (i % 5) for i in range(40)])
    condition = {
        "any": [
            {"indicator": "RSI", "params": {"period": 14}, "op": "<", "value": -1},
            {"indicator": "RSI", "params": {"period": 14}, "op": "<", "value": 100},
        ]
    }
    series = evaluate_condition(candles, condition)
    assert series.dtype == bool
    assert series.any()


def test_not_negates_leg() -> None:
    """``not`` inverts a child condition."""
    candles = _ohlcv([100.0] * 40)
    always_true = {"indicator": "RSI", "params": {"period": 14}, "op": "<", "value": 100}
    series = evaluate_condition(candles, {"not": always_true})
    assert not bool(series.iloc[-1])


def test_nested_all_any() -> None:
    """Nested all/any trees evaluate correctly."""
    candles = _ohlcv([100 + (i % 5) for i in range(40)])
    condition = {
        "all": [
            {"indicator": "RSI", "params": {"period": 14}, "op": "<", "value": 100},
            {
                "any": [
                    {"indicator": "RSI", "params": {"period": 14}, "op": ">", "value": 1000},
                    {"indicator": "ADX", "params": {"period": 14}, "op": ">", "value": -1},
                ]
            },
        ]
    }
    series = evaluate_condition(candles, condition)
    assert series.any()


def test_empty_any_raises() -> None:
    """Empty ``any`` group is invalid."""
    candles = _ohlcv([100.0] * 20)
    with pytest.raises(InvalidSignalError, match="any"):
        evaluate_condition(candles, {"any": []})


def test_mtf_timeframe_asof_ffill_no_lookahead() -> None:
    """Higher-TF leaf aligns via ffill onto base without inventing future truths."""
    base = _ohlcv([10, 11, 12, 13, 14, 15], freq="h", start="2024-01-01")
    daily = pd.DataFrame(
        {
            "ts": pd.to_datetime(["2024-01-01", "2024-01-02"], utc=True),
            "open": [10.0, 20.0],
            "high": [11.0, 21.0],
            "low": [9.0, 19.0],
            "close": [10.0, 20.0],
            "volume": [1.0, 1.0],
        }
    )
    condition = {
        "field": "close",
        "op": "<",
        "value": 15,
        "timeframe": "1d",
    }
    series = evaluate_condition(
        base,
        condition,
        frames={"1d": daily},
        base_timeframe="1h",
    )
    assert len(series) == len(base)
    day1 = base["ts"].dt.date == pd.Timestamp("2024-01-01").date()
    day2 = base["ts"].dt.date == pd.Timestamp("2024-01-02").date()
    assert series[day1].all()
    assert not series[day2].any()


def test_mtf_missing_frame_raises() -> None:
    """Missing frames map entry raises InvalidSignalError when frames is explicit."""
    candles = _ohlcv([100.0] * 10, freq="h")
    condition = {
        "indicator": "RSI",
        "params": {"period": 2},
        "op": "<",
        "value": 50,
        "timeframe": "1d",
    }
    with pytest.raises(InvalidSignalError, match="not provided"):
        evaluate_condition(candles, condition, frames={}, base_timeframe="1h")


def test_collect_condition_timeframes() -> None:
    """Walk nested trees for timeframe references."""
    condition = {
        "all": [
            {
                "indicator": "RSI",
                "params": {"period": 14},
                "op": "<",
                "value": 30,
                "timeframe": "1d",
            },
            {
                "any": [
                    {
                        "indicator": "SMA",
                        "params": {"period": 200},
                        "op": ">",
                        "compare": "close",
                    },
                    {
                        "not": {
                            "indicator": "RSI",
                            "params": {"period": 14},
                            "op": ">",
                            "value": 70,
                            "timeframe": "4h",
                        }
                    },
                ]
            },
        ]
    }
    assert collect_condition_timeframes(condition) == {"1d", "4h"}


def test_scan_multi_symbol_multi_tf(caplog: pytest.LogCaptureFixture) -> None:
    """Cartesian scan emits matches and console alerts for last-bar level hits."""
    frames = {
        ("AAA/USDT", "1h"): _ohlcv([50.0] * 30, freq="h"),
        ("AAA/USDT", "1d"): _ohlcv([50.0] * 30, freq="D"),
        ("BBB/USDT", "1h"): _ohlcv([50.0] * 30, freq="h"),
        ("BBB/USDT", "1d"): _ohlcv([50.0] * 30, freq="D"),
    }

    def loader(symbol: str, timeframe: str, start: str, end: str) -> pd.DataFrame:
        return frames[(symbol, timeframe)].copy()

    condition = {"indicator": "RSI", "params": {"period": 2}, "op": "<", "value": 100}

    with caplog.at_level(logging.INFO, logger="screener.alerts"):
        result = run_scan(
            symbols=["AAA/USDT", "BBB/USDT"],
            timeframes=["1h", "1d"],
            start="2024-01-01",
            end="2024-02-01",
            condition=condition,
            alert_trigger="level",
            loader=loader,
            sink=ConsoleAlertSink(),
        )

    assert result.scanned_pairs == 4
    assert result.alert_count == 4
    assert len(result.matches) == 4
    assert any("ALERT" in rec.message for rec in caplog.records)


def test_edge_vs_level_last_bar() -> None:
    """Edge does not match when condition has been true for many bars."""
    candles = _ohlcv([50.0] * 40)
    level = evaluate_condition(
        candles,
        {"indicator": "RSI", "params": {"period": 2}, "op": "<", "value": 100},
    )
    edge = apply_entry_trigger(level, "edge")
    level_trig = apply_entry_trigger(level, "level")
    assert bool(level_trig.iloc[-1])
    assert not bool(edge.iloc[-1])


def test_scan_symbol_timeframe_empty_returns_none() -> None:
    """Empty candle windows produce no match."""

    def loader(symbol: str, timeframe: str, start: str, end: str) -> pd.DataFrame:
        return pd.DataFrame(columns=["ts", "open", "high", "low", "close", "volume"])

    match = scan_symbol_timeframe(
        "BTC/USDT",
        "1d",
        "2024-01-01",
        "2024-02-01",
        {"indicator": "RSI", "params": {"period": 14}, "op": "<", "value": 30},
        loader=loader,
    )
    assert match is None
