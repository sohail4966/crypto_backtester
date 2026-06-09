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
