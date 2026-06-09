"""
Tests for slippage and commission in the backtest engine (Phase 3 Step 2).
"""

import pandas as pd

from backtest.engine import run_backtest
from backtest.types import BacktestConfig, CommissionConfig


def _simple_candles() -> pd.DataFrame:
    """Two-bar entry and exit scenario."""
    return pd.DataFrame(
        {
            "ts": pd.date_range("2024-01-01", periods=4, freq="D", tz="UTC"),
            "open": [100.0, 100.0, 110.0, 110.0],
            "high": [100.0, 100.0, 110.0, 110.0],
            "low": [100.0, 100.0, 110.0, 110.0],
            "close": [90.0, 105.0, 110.0, 110.0],
            "volume": 1.0,
        }
    )


def test_long_entry_slippage_raises_fill_above_open() -> None:
    """Long entry with 10 bps slippage fills above the raw open."""
    candles = _simple_candles()
    entry_signals = pd.Series([True, False, False, False])
    exit_signals = pd.Series([False, False, True, False])
    config = BacktestConfig(slippage_bps=10.0)

    trades, _equity = run_backtest(
        candles,
        entry_signals,
        exit_signals,
        initial_capital=1000.0,
        backtest_config=config,
    )

    assert len(trades) == 1
    assert trades[0].entry_price == 100.1


def test_commission_reduces_final_capital_vs_zero_fee_baseline() -> None:
    """Commission on entry and exit lowers final capital versus a zero-fee run."""
    candles = _simple_candles()
    entry_signals = pd.Series([True, False, False, False])
    exit_signals = pd.Series([False, False, True, False])

    _trades_free, equity_free = run_backtest(
        candles,
        entry_signals,
        exit_signals,
        initial_capital=1000.0,
    )
    _trades_paid, equity_paid = run_backtest(
        candles,
        entry_signals,
        exit_signals,
        initial_capital=1000.0,
        backtest_config=BacktestConfig(
            commission=CommissionConfig(type="percent", rate=0.001),
        ),
    )

    assert equity_paid.attrs["final_capital"] < equity_free.attrs["final_capital"]
    assert _trades_paid[0].commission_paid > 0
