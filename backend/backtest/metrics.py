"""
Backtest performance metrics and equity curve output.

save_equity_curve writes a PNG to disk; compute_metrics is a pure function.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from backtest.engine import Trade
from backtest.types import BacktestMetrics

EQUITY_FIGURE_WIDTH = 10
EQUITY_FIGURE_HEIGHT = 5
EQUITY_LINE_COLOR = "#2563eb"
EQUITY_DPI = 120

INTRADAY_TIMEFRAMES = frozenset({"1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h"})
TRADING_DAYS_PER_YEAR = 365.0


def _years_elapsed(candles: pd.DataFrame | None) -> float:
    """Approximate elapsed calendar years for CAGR and Calmar."""
    if candles is None or candles.empty:
        return 1.0
    start = pd.to_datetime(candles.iloc[0]["ts"], utc=True)
    end = pd.to_datetime(candles.iloc[-1]["ts"], utc=True)
    days = max((end - start).days, 1)
    return days / 365.25


def _equity_returns_for_risk(
    equity: pd.Series,
    candles: pd.DataFrame | None,
    timeframe: str,
) -> pd.Series:
    """
    Build return series for Sharpe/Sortino.

    Intraday timeframes resample equity to one point per UTC day (D-46).
    """
    if candles is not None and len(candles) == len(equity) and timeframe in INTRADAY_TIMEFRAMES:
        frame = pd.DataFrame(
            {
                "ts": pd.to_datetime(candles["ts"], utc=True),
                "equity": equity.values,
            }
        )
        frame["date"] = frame["ts"].dt.floor("D")
        daily_equity = frame.groupby("date", sort=True)["equity"].last()
        return daily_equity.pct_change().dropna()

    return equity.pct_change().dropna()


def _sharpe_ratio(returns: pd.Series, periods_per_year: float = TRADING_DAYS_PER_YEAR) -> float:
    """Annualized Sharpe ratio from a return series."""
    if len(returns) < 2:
        return 0.0
    std = float(returns.std())
    if std == 0.0:
        return 0.0
    return float(returns.mean() / std * (periods_per_year**0.5))


def _sortino_ratio(returns: pd.Series, periods_per_year: float = TRADING_DAYS_PER_YEAR) -> float:
    """Annualized Sortino ratio using downside deviation only."""
    if len(returns) < 2:
        return 0.0
    downside = returns[returns < 0]
    if downside.empty:
        # No negative periods — Sharpe is a sensible finite proxy.
        return _sharpe_ratio(returns, periods_per_year) if float(returns.mean()) > 0 else 0.0
    downside_std = float(downside.std())
    if downside_std == 0.0:
        return 0.0
    return float(returns.mean() / downside_std * (periods_per_year**0.5))


def _profit_factor(trades: list[Trade]) -> float:
    """Gross wins divided by gross losses in quote PnL."""
    gross_wins = sum(trade.pnl_quote for trade in trades if trade.pnl_quote > 0)
    gross_losses = abs(sum(trade.pnl_quote for trade in trades if trade.pnl_quote < 0))
    if gross_losses == 0.0:
        return float(gross_wins > 0)
    return gross_wins / gross_losses


def _calmar_ratio(total_return: float, max_drawdown: float, years: float) -> float:
    """CAGR divided by absolute max drawdown."""
    if max_drawdown >= 0.0 or years <= 0.0:
        return 0.0
    base = 1.0 + total_return
    if base <= 0.0:
        return 0.0
    cagr = base ** (1.0 / years) - 1.0
    return cagr / abs(max_drawdown)


def compute_metrics(
    trades: list[Trade],
    equity: pd.Series,
    *,
    candles: pd.DataFrame | None = None,
    timeframe: str = "1d",
    benchmark_return: float | None = None,
) -> BacktestMetrics:
    """
    Compute summary statistics from trades and the equity curve.

    Args:
        trades: Closed trades from the backtest engine.
        equity: Per-bar equity Series with initial_capital and final_capital attrs.
        candles: Optional OHLCV frame aligned to equity (for daily resample).
        timeframe: Candle timeframe string (controls Sharpe/Sortino resampling).
        benchmark_return: Optional buy-and-hold total return for alpha.

    Returns:
        BacktestMetrics dict with core and extended risk statistics.
    """
    initial = float(equity.attrs.get("initial_capital", equity.iloc[0]))
    final = float(equity.attrs.get("final_capital", equity.iloc[-1]))
    total_return = (final / initial) - 1.0 if initial else 0.0

    if trades:
        winning_trades = sum(1 for trade in trades if trade.return_pct > 0)
        win_rate = winning_trades / len(trades)
    else:
        win_rate = 0.0

    peak_equity = equity.cummax()
    drawdown = (equity - peak_equity) / peak_equity
    max_drawdown = float(drawdown.min()) if len(equity) else 0.0

    returns = _equity_returns_for_risk(equity, candles, timeframe)
    years = _years_elapsed(candles)

    metrics = BacktestMetrics(
        total_return=total_return,
        win_rate=win_rate,
        max_drawdown=max_drawdown,
        trade_count=len(trades),
        forced_close=bool(equity.attrs.get("forced_close", False)),
        final_capital=final,
        initial_capital=initial,
        sharpe_ratio=_sharpe_ratio(returns),
        sortino_ratio=_sortino_ratio(returns),
        calmar_ratio=_calmar_ratio(total_return, max_drawdown, years),
        profit_factor=_profit_factor(trades),
        benchmark_return=benchmark_return,
        alpha_vs_benchmark=(
            total_return - benchmark_return if benchmark_return is not None else None
        ),
    )
    return metrics


def save_equity_curve(
    equity: pd.Series,
    candles: pd.DataFrame,
    path: str | Path,
) -> Path:
    """
    Save the equity curve as a PNG file.

    Args:
        equity: Per-bar equity values.
        candles: OHLCV DataFrame with a ts column for the x-axis.
        path: Output file path.

    Returns:
        Resolved path to the written PNG.

    Side effects:
        Creates parent directories and writes the image file.
    """
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, axis = plt.subplots(figsize=(EQUITY_FIGURE_WIDTH, EQUITY_FIGURE_HEIGHT))
    dates = candles["ts"]
    axis.plot(dates, equity.values, label="Equity", color=EQUITY_LINE_COLOR)
    axis.set_title("Equity Curve")
    axis.set_xlabel("Date")
    axis.set_ylabel("Capital")
    axis.grid(True, alpha=0.3)
    axis.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_path, dpi=EQUITY_DPI)
    plt.close(fig)
    return output_path
