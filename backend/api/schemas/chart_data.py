"""
Unified chart window schemas (Phase 4b).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from api.schemas.candles import Bar
from api.schemas.indicators import IndicatorPoint, IndicatorSpec
from api.schemas.symbols import SymbolResponse


class Signal(BaseModel):
    """Strategy signal on a bar (populated in Phase 4c)."""

    time: int
    side: str | None = None
    label: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Trade(BaseModel):
    """Executed trade marker (populated in Phase 4c)."""

    time: int
    side: str | None = None
    price: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChartDataResponse(BaseModel):
    """Unified chart payload: symbol, candles, indicators, optional overlays."""

    model_config = ConfigDict(populate_by_name=True)

    symbol: SymbolResponse
    timeframe: str
    start: int
    end: int
    candles: list[Bar]
    indicators: dict[str, list[IndicatorPoint]]
    signals: list[Signal] = Field(default_factory=list)
    trades: list[Trade] = Field(default_factory=list)
    next_start: int | None = Field(default=None, alias="nextStart")


class ReplayRunCreate(BaseModel):
    """Create an in-memory replay run (REST chunk buffering)."""

    model_config = ConfigDict(populate_by_name=True)

    symbol_id: str = Field(alias="symbolId")
    timeframe: str
    start: int
    end: int
    indicators: list[IndicatorSpec] = Field(default_factory=list)
    step_timeframe: str | None = Field(default=None, alias="stepTimeframe")


class ReplayRunResponse(BaseModel):
    """Replay run creation result."""

    model_config = ConfigDict(populate_by_name=True)

    run_id: str = Field(alias="runId")
    symbol_id: str = Field(alias="symbolId")
    timeframe: str
    start: int
    end: int
    total_bars: int = Field(alias="totalBars")


class ReplayTradesResponse(BaseModel):
    """Trades for a replay run (empty until Phase 4c)."""

    model_config = ConfigDict(populate_by_name=True)

    run_id: str = Field(alias="runId")
    trades: list[Trade] = Field(default_factory=list)
