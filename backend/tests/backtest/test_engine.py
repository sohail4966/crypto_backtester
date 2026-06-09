"""
Tests for backtest.engine — especially next-bar open execution (D-14).
"""

import pandas as pd
import pytest

from backtest.engine import run_backtest


def test_entry_executes_at_next_bar_open() -> None:
    """
    Entry signal on bar 0 must fill at open of bar 1, not close of bar 0.

    Bar 0 close is 90 but open of bar 1 is 100 — fill price must be 100.
    """
    candles = pd.DataFrame(
        {
            "ts": pd.date_range("2024-01-01", periods=4, freq="D", tz="UTC"),
            "open": [100.0, 100.0, 110.0, 110.0],
            "high": [100.0, 100.0, 110.0, 110.0],
            "low": [100.0, 100.0, 110.0, 110.0],
            "close": [90.0, 105.0, 110.0, 110.0],
            "volume": 1.0,
        }
    )
    entry_signals = pd.Series([True, False, False, False])
    exit_signals = pd.Series([False, False, True, False])

    trades, _equity = run_backtest(
        candles,
        entry_signals,
        exit_signals,
        initial_capital=1000.0,
    )

    assert len(trades) == 1
    assert trades[0].entry_price == 100.0
    assert trades[0].exit_price == 110.0
    assert trades[0].side == "long"
    assert trades[0].exit_reason == "signal"


def test_short_entry_executes_with_inverted_return() -> None:
    """Short positions profit when price falls after entry."""
    candles = pd.DataFrame(
        {
            "ts": pd.date_range("2024-01-01", periods=4, freq="D", tz="UTC"),
            "open": [100.0, 100.0, 90.0, 90.0],
            "high": [100.0, 100.0, 90.0, 90.0],
            "low": [100.0, 100.0, 90.0, 90.0],
            "close": [100.0, 100.0, 90.0, 90.0],
            "volume": 1.0,
        }
    )
    long_entry = pd.Series([False, False, False, False])
    long_exit = pd.Series([False, False, False, False])
    short_entry = pd.Series([True, False, False, False])
    short_exit = pd.Series([False, False, True, False])

    trades, _equity = run_backtest(
        candles,
        long_entry,
        long_exit,
        initial_capital=1000.0,
        short_entry_signals=short_entry,
        short_exit_signals=short_exit,
    )

    assert len(trades) == 1
    assert trades[0].side == "short"
    assert trades[0].entry_price == 100.0
    assert trades[0].exit_price == 90.0
    assert trades[0].return_pct == pytest.approx(11.111111, rel=1e-4)


def test_long_stop_loss_exits_before_signal() -> None:
    """ATR stop loss closes the position when the bar low breaches the stop."""
    candles = pd.DataFrame(
        {
            "ts": pd.date_range("2024-01-01", periods=4, freq="D", tz="UTC"),
            "open": [100.0, 100.0, 95.0, 95.0],
            "high": [100.0, 100.0, 96.0, 96.0],
            "low": [100.0, 100.0, 90.0, 90.0],
            "close": [100.0, 100.0, 92.0, 92.0],
            "volume": 1.0,
        }
    )
    entry_signals = pd.Series([True, False, False, False])
    exit_signals = pd.Series([False, False, False, True])
    atr_series = pd.Series([2.0, 2.0, 2.0, 2.0])
    side = {
        "entry": {"indicator": "RSI", "op": "<", "value": 30},
        "exit": {"indicator": "RSI", "op": ">", "value": 70},
        "stop_loss": {"type": "atr", "period": 14, "multiplier": 2.0},
        "take_profit": {"type": "risk_reward", "ratio": 2.0},
    }

    trades, _equity = run_backtest(
        candles,
        entry_signals,
        exit_signals,
        initial_capital=1000.0,
        long_side=side,
        atr_series=atr_series,
    )

    assert len(trades) == 1
    assert trades[0].exit_reason == "stop_loss"
    assert trades[0].exit_price == 96.0
