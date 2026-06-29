"""
Bar replay session schemas (REST + WebSocket v2).

Open-ended sessions start at ``start`` and run until the latest stored candle
or user stop. Playback control is WebSocket-only; REST provides create/state/delete.
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from api.schemas.indicators import IndicatorSpec


class ReplaySessionCreate(BaseModel):
    """
    Request body for ``POST /api/v1/replay/sessions``.

    Attributes:
        symbol: Trading pair (must exist in ``app.symbols``).
        timeframe: Chart display timeframe (e.g. ``1h``).
        start: Replay start anchor (unix seconds); no ``end`` — open-ended.
        indicators: Overlay specs to precompute (default: none).
        step_timeframe: Bar step resolution; defaults to ``timeframe``.
        speed: Initial playback speed (1× = 1 bar/sec on client).
        autoplay: Send first ``tick_batch`` on WebSocket connect.
        user_id: Optional; logging only until auth (Phase 11).
    """

    symbol: str
    timeframe: str
    start: int
    indicators: list[IndicatorSpec] = Field(default_factory=list)
    step_timeframe: str | None = None
    speed: float = Field(default=1.0, gt=0)
    autoplay: bool = False
    user_id: UUID | None = None


class ReplaySessionResponse(BaseModel):
    """
    Response from session create.

    Attributes:
        session_id: New session UUID.
        ws_url: WebSocket path (prepend API host/ws scheme).
    """

    session_id: UUID
    ws_url: str


class ReplayStateResponse(BaseModel):
    """
    Session snapshot for REST and WS ``replay_state`` events.

    Serialized with camelCase aliases for WebSocket clients.
    """

    model_config = ConfigDict(populate_by_name=True)

    session_id: UUID
    symbol: str
    timeframe: str
    step_timeframe: str
    start: int = Field(alias="startAnchor")
    latest_available: int | None = Field(default=None, alias="latestAvailable")
    cursor: int | None = None
    state: Literal["idle", "playing", "paused", "completed"]
    speed: float
    bar_index: int = Field(alias="barIndex")
    queue_remaining: int = Field(alias="queueRemaining")
    indicators: list[IndicatorSpec]


class ReplayWsCommand(BaseModel):
    """
    WebSocket client command (JSON text frame).

    Actions:
        play: Start playback; optional ``speed``; server sends ``tick_batch``.
        pause: Pause and checkpoint cursor.
        step: Manual advance; optional ``count`` (default batch size).
        seek: Jump to ``to`` unix timestamp.
        set_speed: Update speed multiplier.
        set_indicators: Replace overlays; server sends ``buffer_reset`` + ``snapshot``.
        get_state: Return ``replay_state`` only.
        refill: Request another full ``tick_batch`` for client queue top-up.
    """

    action: Literal[
        "play",
        "pause",
        "step",
        "seek",
        "set_speed",
        "set_indicators",
        "get_state",
        "refill",
    ]
    speed: float | None = None
    count: int | None = None
    to: int | None = None
    indicators: list[IndicatorSpec] | None = None


class ReplayTickPayload(BaseModel):
    """One element inside a ``tick_batch`` ticks array."""

    bar: dict[str, Any]
    indicators: dict[str, dict[str, Any]]


class ReplayTickBatchEvent(BaseModel):
    """
    Server ``tick_batch`` WebSocket event.

    ``queue_remaining`` tells the client when to send ``refill``.
    """

    type: Literal["tick_batch"] = "tick_batch"
    ticks: list[ReplayTickPayload]
    cursor: int | None
    queue_remaining: int = Field(alias="queueRemaining")
