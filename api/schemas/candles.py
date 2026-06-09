"""
Historical candle schemas.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Bar(BaseModel):
    """Single OHLCV bar for chart clients (time in unix seconds UTC)."""

    time: int
    open: float
    high: float
    low: float
    close: float
    volume: float


class CandlesResponse(BaseModel):
    """Paginated historical candles."""

    symbol: str
    timeframe: str
    bars: list[Bar]
    next_from: int | None = None
