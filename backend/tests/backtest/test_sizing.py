"""
Tests for position sizing (Phase 3 Step 3).
"""

import pandas as pd
import pytest

from backtest.engine import run_backtest
from backtest.sizing import compute_position_notional
from backtest.types import BacktestConfig, SizingConfig
from signals.types import StopLossConfig


def test_compute_position_notional_fixed_pct() -> None:
    """fixed_pct allocates a fraction of current equity."""
    sizing = SizingConfig(mode="fixed_pct", pct=0.5)
    notional = compute_position_notional(sizing, equity=10_000.0, entry_fill=100.0, side="long")
    assert notional == 5_000.0


def test_compute_position_notional_fixed_notional_skips_when_insufficient() -> None:
    """fixed_notional returns zero when cash is below the configured amount."""
    sizing = SizingConfig(mode="fixed_notional", amount=1_000.0)
    notional = compute_position_notional(sizing, equity=500.0, entry_fill=100.0, side="long")
    assert notional == 0.0


def test_compute_position_notional_risk_pct_scales_inversely_with_atr() -> None:
    """risk_pct notional shrinks when ATR stop distance widens."""
    sizing = SizingConfig(mode="risk_pct", risk_pct=0.01)
    stop: StopLossConfig = {"type": "atr", "period": 14, "multiplier": 2.0}
    small_atr = compute_position_notional(
        sizing,
        equity=10_000.0,
        entry_fill=100.0,
        side="long",
        atr_value=1.0,
        stop_loss=stop,
    )
    large_atr = compute_position_notional(
        sizing,
        equity=10_000.0,
        entry_fill=100.0,
        side="long",
        atr_value=4.0,
        stop_loss=stop,
    )
    assert small_atr > large_atr
    assert small_atr == pytest.approx(5_000.0)
    assert large_atr == pytest.approx(1_250.0)


def test_fixed_pct_deploys_half_notional_per_trade() -> None:
    """fixed_pct 0.5 allocates half of equity to each trade, not 100%."""
    candles = pd.DataFrame(
        {
            "ts": pd.date_range("2024-01-01", periods=4, freq="D", tz="UTC"),
            "open": [100.0, 100.0, 110.0, 110.0],
            "high": [100.0, 100.0, 110.0, 110.0],
            "low": [100.0, 100.0, 110.0, 110.0],
            "close": [100.0, 100.0, 110.0, 110.0],
            "volume": 1.0,
        }
    )
    entry_signals = pd.Series([True, False, False, False])
    exit_signals = pd.Series([False, False, True, False])
    config = BacktestConfig(sizing=SizingConfig(mode="fixed_pct", pct=0.5))

    trades, equity = run_backtest(
        candles,
        entry_signals,
        exit_signals,
        initial_capital=10_000.0,
        backtest_config=config,
    )

    assert len(trades) == 1
    assert trades[0].size == pytest.approx(5_000.0)
    # Exit proceeds added to ~5k cash reserve → total above full-capital-only return on same move.
    assert equity.attrs["final_capital"] > 10_000.0
    assert equity.attrs["final_capital"] <= 10_500.0
