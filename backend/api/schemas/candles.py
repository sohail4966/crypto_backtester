"""
Historical candle schemas.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


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


class CandleDataRangeResponse(BaseModel):
    """Available stored candle range for chart window anchoring."""

    model_config = ConfigDict(populate_by_name=True)

    symbol_id: str = Field(alias="symbolId")
    timeframe: str
    earliest: int | None = Field(
        default=None,
        description="Unix seconds UTC of oldest stored bar, or null when empty",
    )
    latest: int | None = Field(
        default=None,
        description="Unix seconds UTC of newest stored bar, or null when empty",
    )
    bar_count: int = Field(default=0, alias="barCount")
