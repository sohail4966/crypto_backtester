"""
Typed structures for backtest outputs.
"""

from __future__ import annotations

from typing import TypedDict


class BacktestMetrics(TypedDict):
    """Summary statistics produced after a backtest run."""

    total_return: float
    win_rate: float
    max_drawdown: float
    trade_count: int
    forced_close: bool
    final_capital: float
    initial_capital: float
