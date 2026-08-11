"""
Meta endpoint response schemas.
"""

from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check payload."""

    status: str
    version: str
    database: str


class TimeframesResponse(BaseModel):
    """Supported candle timeframes."""

    timeframes: list[str]
    notes: dict[str, str] = {
        "1M": "Calendar month buckets (UTC); seek/warmup use calendar math, not fixed 30 days.",
    }
