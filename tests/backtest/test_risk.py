"""
Tests for stop loss, take profit, and trailing stop logic (Phase 3 Step 4).
"""

import pandas as pd
import pytest

from backtest.engine import run_backtest
from backtest.risk import (
    compute_initial_stop,
    compute_take_profit_target,
    resolve_risk_levels,
    update_trailing_stop,
)


def test_fixed_stop_triggers_at_configured_offset() -> None:
    """Fixed stop loss uses offset_pct below entry for longs."""
    candles = pd.DataFrame(
        {
            "ts": pd.date_range("2024-01-01", periods=4, freq="D", tz="UTC"),
            "open": [100.0, 100.0, 100.0, 100.0],
            "high": [100.0, 100.0, 100.0, 100.0],
            "low": [100.0, 100.0, 94.0, 94.0],
            "close": [100.0, 100.0, 96.0, 96.0],
            "volume": 1.0,
        }
    )
    entry_signals = pd.Series([True, False, False, False])
    exit_signals = pd.Series([False, False, False, True])
    side = {
        "entry": {"indicator": "RSI", "op": "<", "value": 30},
        "exit": {"indicator": "RSI", "op": ">", "value": 70},
        "stop_loss": {"type": "fixed", "offset_pct": 0.05},
        "take_profit": {"type": "fixed", "offset_pct": 0.20},
    }

    trades, _equity = run_backtest(
        candles,
        entry_signals,
        exit_signals,
        initial_capital=1000.0,
        long_side=side,
    )

    assert len(trades) == 1
    assert trades[0].exit_reason == "stop_loss"
    assert trades[0].exit_price == pytest.approx(95.0)


def test_fixed_take_profit_triggers_before_signal() -> None:
    """Fixed take profit exits when high reaches the target."""
    candles = pd.DataFrame(
        {
            "ts": pd.date_range("2024-01-01", periods=4, freq="D", tz="UTC"),
            "open": [100.0, 100.0, 100.0, 100.0],
            "high": [100.0, 100.0, 110.0, 110.0],
            "low": [100.0, 100.0, 100.0, 100.0],
            "close": [100.0, 100.0, 108.0, 108.0],
            "volume": 1.0,
        }
    )
    entry_signals = pd.Series([True, False, False, False])
    exit_signals = pd.Series([False, False, False, True])
    side = {
        "entry": {"indicator": "RSI", "op": "<", "value": 30},
        "exit": {"indicator": "RSI", "op": ">", "value": 70},
        "stop_loss": {"type": "fixed", "offset_pct": 0.20},
        "take_profit": {"type": "fixed", "offset_pct": 0.10},
    }

    trades, _equity = run_backtest(
        candles,
        entry_signals,
        exit_signals,
        initial_capital=1000.0,
        long_side=side,
    )

    assert len(trades) == 1
    assert trades[0].exit_reason == "take_profit"
    assert trades[0].exit_price == pytest.approx(110.0)


def test_trailing_stop_ratchet_moves_up_never_down_for_long() -> None:
    """ATR trailing stop ratchets up with new highs and never moves down."""
    stop_loss = {"type": "atr_trail", "period": 14, "multiplier": 2.0}
    stop, best = update_trailing_stop("long", 96.0, 100.0, 120.0, 115.0, stop_loss, atr_value=2.0)
    assert best == 120.0
    assert stop == pytest.approx(116.0)

    stop_after_pullback, best_after = update_trailing_stop(
        "long", stop, best, 118.0, 112.0, stop_loss, atr_value=2.0
    )
    assert best_after == 120.0
    assert stop_after_pullback == pytest.approx(116.0)


def test_trailing_stop_not_checked_on_entry_bar() -> None:
    """Trailing stop does not exit on the same bar as entry (D-41)."""
    candles = pd.DataFrame(
        {
            "ts": pd.date_range("2024-01-01", periods=4, freq="D", tz="UTC"),
            "open": [100.0, 100.0, 100.0, 100.0],
            "high": [100.0, 100.0, 105.0, 105.0],
            "low": [100.0, 100.0, 90.0, 90.0],
            "close": [100.0, 100.0, 95.0, 95.0],
            "volume": 1.0,
        }
    )
    entry_signals = pd.Series([True, False, False, False])
    exit_signals = pd.Series([False, False, False, True])
    atr_series = pd.Series([2.0, 2.0, 2.0, 2.0])
    side = {
        "entry": {"indicator": "RSI", "op": "<", "value": 30},
        "exit": {"indicator": "RSI", "op": ">", "value": 70},
        "stop_loss": {"type": "atr_trail", "period": 14, "multiplier": 2.0},
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
    # Entry bar 1; bar 2 low 90 would hit initial stop 96 on entry bar if checked — must wait.
    assert trades[0].exit_reason == "trailing_stop"
    assert trades[0].exit_date == candles.iloc[2]["ts"]


def test_compute_initial_stop_and_take_profit_units() -> None:
    """Unit-level stop and target math for fixed and ATR modes."""
    stop = compute_initial_stop(100.0, "long", {"type": "fixed", "offset_pct": 0.05}, atr_value=0.0)
    assert stop == pytest.approx(95.0)

    levels = resolve_risk_levels(
        100.0,
        "long",
        {"type": "atr", "period": 14, "multiplier": 2.0},
        {"type": "risk_reward", "ratio": 2.0},
        atr_value=2.0,
    )
    assert levels is not None
    assert levels.stop_price == pytest.approx(96.0)
    assert levels.target_price == pytest.approx(compute_take_profit_target(
        100.0, "long", {"type": "risk_reward", "ratio": 2.0}, stop_price=96.0
    ))
