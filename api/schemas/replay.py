"""
Bar replay session schemas.
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from api.schemas.indicators import IndicatorSpec


class ReplaySessionCreate(BaseModel):
    """Create replay session request."""

    symbol: str
    timeframe: str
    start: int
    end: int
    indicators: list[IndicatorSpec] = Field(default_factory=list)
    step_timeframe: str | None = None
    speed: float = Field(default=1.0, gt=0)
    autoplay: bool = False
    user_id: UUID | None = None


class ReplaySessionResponse(BaseModel):
    """Replay session creation result."""

    session_id: UUID
    ws_url: str


class ReplayStateResponse(BaseModel):
    """Replay session snapshot."""

    session_id: UUID
    symbol: str
    timeframe: str
    step_timeframe: str
    start: int
    end: int
    cursor: int | None
    state: Literal["idle", "playing", "paused", "completed"]
    speed: float
    bar_index: int
    total_bars: int
    indicators: list[IndicatorSpec]


class ReplayWsCommand(BaseModel):
    """WebSocket client command."""

    action: Literal[
        "play",
        "pause",
        "step",
        "seek",
        "set_speed",
        "set_step_timeframe",
        "set_indicators",
        "get_state",
    ]
    speed: float | None = None
    count: int | None = None
    to: int | None = None
    step_timeframe: str | None = None
    indicators: list[IndicatorSpec] | None = None
