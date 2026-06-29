"""
Unified chart window schemas (Phase 4b).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from api.schemas.candles import Bar
from api.schemas.indicators import IndicatorPoint
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
