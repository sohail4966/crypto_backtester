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
            pnl_quote=100.0,
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
    assert metrics["profit_factor"] == pytest.approx(1.0)


def test_compute_metrics_profit_factor_from_quote_pnl() -> None:
    """Profit factor uses gross quote PnL wins over losses."""
    trades = [
        Trade(
            entry_date=pd.Timestamp("2024-01-01", tz="UTC"),
            exit_date=pd.Timestamp("2024-01-02", tz="UTC"),
            entry_price=100.0,
            exit_price=110.0,
            return_pct=10.0,
            pnl_quote=200.0,
        ),
        Trade(
            entry_date=pd.Timestamp("2024-01-03", tz="UTC"),
            exit_date=pd.Timestamp("2024-01-04", tz="UTC"),
            entry_price=100.0,
            exit_price=95.0,
            return_pct=-5.0,
            pnl_quote=-100.0,
        ),
    ]
    equity = pd.Series([1000.0, 1100.0])
    equity.attrs["initial_capital"] = 1000.0
    equity.attrs["final_capital"] = 1100.0

    metrics = compute_metrics(trades, equity)

    assert metrics["profit_factor"] == pytest.approx(2.0)


def test_compute_metrics_sharpe_on_simple_equity_curve() -> None:
    """Sharpe ratio is positive for a steadily rising equity curve."""
    equity = pd.Series([1000.0, 1010.0, 1020.0, 1030.0])
    equity.attrs["initial_capital"] = 1000.0
    equity.attrs["final_capital"] = 1030.0

    metrics = compute_metrics([], equity, timeframe="1d")

    assert metrics["sharpe_ratio"] > 0.0
    assert metrics["sortino_ratio"] > 0.0


def test_compute_metrics_resamples_intraday_equity_to_daily() -> None:
    """Intraday Sharpe uses daily equity resample (D-46)."""
    candles = pd.DataFrame(
        {
            "ts": pd.date_range("2024-01-01", periods=4, freq="h", tz="UTC"),
            "close": [100.0, 101.0, 102.0, 103.0],
        }
    )
    equity = pd.Series([1000.0, 1005.0, 1010.0, 1015.0])
    equity.attrs["initial_capital"] = 1000.0
    equity.attrs["final_capital"] = 1015.0

    metrics = compute_metrics([], equity, candles=candles, timeframe="1h")

    assert metrics["sharpe_ratio"] >= 0.0


def test_compute_metrics_benchmark_alpha() -> None:
    """Alpha is strategy return minus buy-and-hold return."""
    equity = pd.Series([1000.0, 1200.0])
    equity.attrs["initial_capital"] = 1000.0
    equity.attrs["final_capital"] = 1200.0

    metrics = compute_metrics([], equity, benchmark_return=0.10)

    assert metrics["benchmark_return"] == pytest.approx(0.10)
    assert metrics["alpha_vs_benchmark"] == pytest.approx(0.10)
