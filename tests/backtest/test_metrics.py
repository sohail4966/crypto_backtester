"""
Tests for backtest.metrics.
"""

import pandas as pd
import pytest

from backtest.engine import Trade
from backtest.metrics import compute_metrics


def test_compute_metrics_win_rate_and_total_return() -> None:
    """Metrics reflect one winning trade on doubled capital."""
    trades = [
        Trade(
            entry_date=pd.Timestamp("2024-01-01", tz="UTC"),
            exit_date=pd.Timestamp("2024-02-01", tz="UTC"),
            entry_price=100.0,
            exit_price=110.0,
            return_pct=10.0,
        )
    ]
    equity = pd.Series([1000.0, 1100.0])
    equity.attrs["initial_capital"] = 1000.0
    equity.attrs["final_capital"] = 1100.0
    equity.attrs["forced_close"] = False

    metrics = compute_metrics(trades, equity)

    assert metrics["trade_count"] == 1
    assert metrics["win_rate"] == 1.0
    assert metrics["total_return"] == pytest.approx(0.1)
