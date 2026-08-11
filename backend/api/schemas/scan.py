"""
Pydantic schemas for the screener HTTP API (Phase 8).
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ScanCreateRequest(BaseModel):
    """Request body for ``POST /scan``."""

    timeframes: list[str] = Field(min_length=1)
    start: int = Field(description="Inclusive window start (unix seconds UTC)")
    end: int = Field(description="Inclusive window end (unix seconds UTC)")
    condition: dict[str, Any]
    symbols: list[str] | None = None
    alert_trigger: Literal["edge", "level"] = "edge"
    persist: bool = True

    @model_validator(mode="after")
    def validate_window(self) -> ScanCreateRequest:
        """Ensure start <= end and timeframes are non-empty strings."""
        if self.start > self.end:
            raise ValueError("start must be <= end")
        cleaned = [tf.strip() for tf in self.timeframes if tf and tf.strip()]
        if not cleaned:
            raise ValueError("timeframes must contain at least one value")
        self.timeframes = cleaned
        return self


class ScanMatchResponse(BaseModel):
    """One matching symbol×timeframe."""

    symbol: str
    timeframe: str
    bar_ts: str
    triggered: bool
    close: float | None = None


class ScanErrorResponse(BaseModel):
    """Per-pair evaluation error."""

    symbol: str
    timeframe: str
    error: str


class ScanRunResponse(BaseModel):
    """Response for ``POST /scan``."""

    scan_id: UUID | None
    timeframes: list[str]
    symbols: list[str]
    start: int
    end: int
    alert_trigger: Literal["edge", "level"]
    matches: list[ScanMatchResponse]
    alert_count: int
    duration_ms: int
    scanned_pairs: int
    errors: list[ScanErrorResponse] = Field(default_factory=list)
    persisted: bool
