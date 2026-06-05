"""
Tests for backtest.engine — especially next-bar open execution (D-14).
"""

import pandas as pd

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
