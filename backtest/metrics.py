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


def compute_metrics(trades: list[Trade], equity: pd.Series) -> BacktestMetrics:
    """
    Compute summary statistics from trades and the equity curve.

    Args:
        trades: Closed trades from the backtest engine.
        equity: Per-bar equity Series with initial_capital and final_capital attrs.

    Returns:
        BacktestMetrics dict with return, win rate, drawdown, and trade count.
    """
    initial = float(equity.attrs.get("initial_capital", equity.iloc[0]))
    final = float(equity.attrs.get("final_capital", equity.iloc[-1]))
    total_return = (final / initial) - 1.0 if initial else 0.0

    if trades:
        winning_trades = sum(1 for trade in trades if trade.return_pct > 0)
        win_rate = winning_trades / len(trades)
    else:
        win_rate = 0.0

    # Drawdown is negative; min() yields the deepest peak-to-trough decline.
    peak_equity = equity.cummax()
    drawdown = (equity - peak_equity) / peak_equity
    max_drawdown = float(drawdown.min()) if len(equity) else 0.0

    return BacktestMetrics(
        total_return=total_return,
        win_rate=win_rate,
        max_drawdown=max_drawdown,
        trade_count=len(trades),
        forced_close=bool(equity.attrs.get("forced_close", False)),
        final_capital=final,
        initial_capital=initial,
    )


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
    # Release the figure so repeated POC runs do not leak memory in long sessions.
    plt.close(fig)
    return output_path
