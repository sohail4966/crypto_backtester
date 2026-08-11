"""
Pydantic schemas for the backtest HTTP API (Phase 4d).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from api.schemas.chart_data import Signal, Trade


class BacktestCommissionBody(BaseModel):
    """Optional commission override for a run."""

    type: Literal["percent", "flat"] = "percent"
    rate: float = 0.0
    amount: float = 0.0


class BacktestSizingBody(BaseModel):
    """Optional sizing override for a run."""

    mode: Literal["full_capital", "fixed_pct", "fixed_notional", "risk_pct"] = "full_capital"
    pct: float = 1.0
    amount: float = 0.0
    risk_pct: float = 0.0


class BacktestParamsBody(BaseModel):
    """Optional global simulation knobs (costs / sizing)."""

    slippage_bps: float | None = None
    commission: BacktestCommissionBody | None = None
    sizing: BacktestSizingBody | None = None


class BacktestCreateRequest(BaseModel):
    """Request body for ``POST /backtest``."""

    symbol: str
    timeframe: str
    start: int = Field(description="Inclusive window start (unix seconds UTC)")
    end: int = Field(description="Inclusive window end (unix seconds UTC)")
    initial_capital: float | None = None
    strategy_name: str | None = None
    strategy: dict[str, Any] | None = None
    backtest: BacktestParamsBody | None = None
    user_id: UUID | None = None

    @model_validator(mode="after")
    def exactly_one_strategy(self) -> BacktestCreateRequest:
        """Require exactly one of strategy_name or strategy."""
        has_name = bool(self.strategy_name and self.strategy_name.strip())
        has_inline = self.strategy is not None
        if has_name == has_inline:
            raise ValueError("Provide exactly one of strategy_name or strategy")
        if self.start > self.end:
            raise ValueError("start must be <= end")
        return self


class EquityPoint(BaseModel):
    """One equity curve sample."""

    time: int
    value: float


class BacktestMetricsResponse(BaseModel):
    """Summary metrics from ``compute_metrics``."""

    total_return: float
    win_rate: float
    max_drawdown: float
    trade_count: int
    forced_close: bool
    final_capital: float
    initial_capital: float
    sharpe_ratio: float | None = None
    sortino_ratio: float | None = None
    calmar_ratio: float | None = None
    profit_factor: float | None = None
    benchmark_return: float | None = None
    alpha_vs_benchmark: float | None = None


class TradeDetail(BaseModel):
    """One completed round-trip from the engine trade log."""

    entry_time: int
    exit_time: int
    entry_price: float
    exit_price: float
    side: str
    exit_reason: str
    forced_close: bool
    return_pct: float
    size: float
    commission_paid: float
    pnl_quote: float


class StrategyInfo(BaseModel):
    """Named strategy catalog entry."""

    name: str
    kind: Literal["dual", "long_only"]


class StrategiesResponse(BaseModel):
    """Catalog of strategies from server config.yaml."""

    strategies: list[StrategyInfo]


class BacktestRunResponse(BaseModel):
    """Persisted backtest run summary (create + get)."""

    run_id: UUID
    symbol: str
    timeframe: str
    start: int
    end: int
    initial_capital: float
    strategy_name: str | None = None
    status: str
    metrics: BacktestMetricsResponse
    equity: list[EquityPoint] = Field(default_factory=list)
    signals: list[Signal] = Field(default_factory=list)
    trades: list[Trade] = Field(default_factory=list)
    created_at: datetime


class BacktestTradesResponse(BaseModel):
    """Full round-trip trade log for a run."""

    run_id: UUID
    trades: list[TradeDetail]
