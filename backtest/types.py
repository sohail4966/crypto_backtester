"""
Typed structures and config dataclasses for backtest inputs and outputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, NotRequired, TypedDict

PositionSide = Literal["long", "short"]
ExitReason = Literal[
    "signal",
    "stop_loss",
    "take_profit",
    "trailing_stop",
    "forced_close",
]
SizingMode = Literal["full_capital", "fixed_pct", "fixed_notional", "risk_pct"]
CommissionType = Literal["percent", "flat"]
BenchmarkMode = Literal["symbol", "none"]


@dataclass(frozen=True)
class CommissionConfig:
    """Commission charged per fill."""

    type: CommissionType = "percent"
    rate: float = 0.0
    amount: float = 0.0


@dataclass(frozen=True)
class SizingConfig:
    """Position sizing defaults for a backtest run."""

    mode: SizingMode = "full_capital"
    pct: float = 1.0
    amount: float = 0.0
    risk_pct: float = 0.0


@dataclass(frozen=True)
class BacktestConfig:
    """Global backtest simulation settings from config.yaml."""

    slippage_bps: float = 0.0
    commission: CommissionConfig = field(default_factory=CommissionConfig)
    sizing: SizingConfig = field(default_factory=SizingConfig)
    export_trades: bool = True
    trades_csv: Path = field(default_factory=lambda: Path("output/trades.csv"))


class BacktestMetrics(TypedDict):
    """Summary statistics produced after a backtest run."""

    total_return: float
    win_rate: float
    max_drawdown: float
    trade_count: int
    forced_close: bool
    final_capital: float
    initial_capital: float
    sharpe_ratio: NotRequired[float]
    sortino_ratio: NotRequired[float]
    calmar_ratio: NotRequired[float]
    profit_factor: NotRequired[float]
    benchmark_return: NotRequired[float | None]
    alpha_vs_benchmark: NotRequired[float | None]
