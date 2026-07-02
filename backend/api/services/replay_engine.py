"""
Replay cursor engine with rolling buffer and overlay precompute.

Orchestrates buffer load/extend/trim, seek, and tick-batch slicing for one
open-ended replay session. All candle I/O uses ``step_timeframe``; ``timeframe``
is display metadata only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from uuid import UUID

import pandas as pd
import psycopg

from api import settings
from api.exceptions import ValidationError
from api.repositories.replay_repository import ReplaySessionRow, ReplayState
from api.schemas.indicators import IndicatorSpec
from api.schemas.replay import ReplayStateResponse
from api.services.candle_service import CandleService
from api.services.overlay_pipeline import OverlayPipeline
from api.services.replay_buffer import ReplayBuffer, ReplayTick
from api.services.timeframes import TIMEFRAME_SECONDS, advance_unix_by_bars, shift_unix_by_bars, validate_timeframe

ReplayExtendResult = Literal["none", "loading", "ready", "completed"]


@dataclass
class ReplayEngine:
    """
    Cursor, extend, trim, seek, and tick slicing for one replay session.

    Attributes:
        session_id: Session UUID.
        symbol: Trading pair.
        timeframe: Chart display timeframe (metadata).
        step_timeframe: Bar resolution for stepping and DB loads.
        start_anchor: User-selected replay start (unix seconds).
        speed: Playback speed multiplier (client uses for interval).
        state: Current playback state.
        indicators: Active indicator specifications.
        buffer: In-memory rolling OHLCV + overlay buffer.
    """

    session_id: UUID
    symbol: str
    timeframe: str
    step_timeframe: str
    start_anchor: int
    speed: float
    state: ReplayState
    indicators: list[IndicatorSpec]
    buffer: ReplayBuffer = field(default_factory=ReplayBuffer)
    _pipeline: OverlayPipeline = field(default_factory=OverlayPipeline)
    _candles: CandleService = field(default_factory=CandleService)

    @classmethod
    def from_row(
        cls,
        row: ReplaySessionRow,
        *,
        buffer: ReplayBuffer | None = None,
        candle_service: CandleService | None = None,
        pipeline: OverlayPipeline | None = None,
    ) -> ReplayEngine:
        """
        Construct an engine from a persisted ``ReplaySessionRow``.

        Does not load candles; call ``load_buffer`` after construction.

        Args:
            row: Database session row.
            buffer: Optional existing buffer (default: empty).
            candle_service: Candle loader (default: new instance).
            pipeline: Overlay pipeline (default: new instance).

        Returns:
            Engine with metadata populated from ``row``.
        """
        return cls(
            session_id=row.session_id,
            symbol=row.symbol,
            timeframe=row.timeframe,
            step_timeframe=row.step_timeframe,
            start_anchor=row.start_anchor,
            speed=row.speed,
            state=row.state,
            indicators=list(row.indicators),
            buffer=buffer or ReplayBuffer(),
            _pipeline=pipeline or OverlayPipeline(),
            _candles=candle_service or CandleService(),
        )

    def cursor_ts(self) -> int | None:
        """
        Current cursor bar time.

        Returns:
            Unix seconds of last revealed bar, or ``None`` before first step.
        """
        return self.buffer.cursor_ts

    def latest_available_ts(self) -> int | None:
        """
        Latest stored candle for this symbol and step timeframe.

        Returns:
            Unix seconds of newest DB candle, or ``None`` when series is empty.
        """
        return self.buffer.latest_available_ts

    def to_state_response(self) -> ReplayStateResponse:
        """
        Build REST/WS ``replay_state`` payload.

        Returns:
            Session snapshot with cursor, queue depth, and indicator specs.
        """
        visible_bars = max(0, self.buffer.cursor_idx - self.buffer.window_start_idx + 1)
        if self.buffer.cursor_idx < self.buffer.window_start_idx:
            visible_bars = 0
        return ReplayStateResponse(
            session_id=self.session_id,
            symbol=self.symbol,
            timeframe=self.timeframe,
            step_timeframe=self.step_timeframe,
            start=self.start_anchor,
            latest_available=self.buffer.latest_available_ts,
            cursor=self.buffer.cursor_ts,
            state=self.state,
            speed=self.speed,
            bar_index=visible_bars,
            queue_remaining=self.buffer.queue_remaining(),
            indicators=self.indicators,
        )

    def _refresh_latest_available(self, conn: psycopg.Connection) -> None:
        """
        Refresh ``latest_available_ts`` from the database.

        Open-ended replay must detect newly synced candles without restart.
        """
        _, latest_ts, _ = self._candles.get_data_range(conn, self.symbol, self.step_timeframe)
        if latest_ts is not None:
            self.buffer.latest_available_ts = latest_ts
        elif not self.buffer.frame.empty:
            self.buffer.latest_available_ts = int(self.buffer.frame.iloc[-1]["ts"].timestamp())

    def load_buffer(self, conn: psycopg.Connection, *, cursor_ts: int | None = None) -> None:
        """
        Load or reload the buffer from database candles at session start.

        Fetches warmup + trail + prefetch bars from ``start_anchor`` forward,
        capped at the latest stored candle.

        Args:
            conn: Database connection.
            cursor_ts: Last revealed bar time; defaults to one bar before
                ``start_anchor`` for a fresh session.
        """
        try:
            validate_timeframe(self.timeframe)
            validate_timeframe(self.step_timeframe)
        except ValueError as exc:
            raise ValidationError("INVALID_TIMEFRAME", str(exc)) from exc

        _, latest_ts, _ = self._candles.get_data_range(conn, self.symbol, self.step_timeframe)
        warmup = self._pipeline.warmup_bars(self.indicators, self.step_timeframe)
        prefetch = settings.replay_prefetch_bars()
        load_to = advance_unix_by_bars(self.start_anchor, self.step_timeframe, prefetch)
        if latest_ts is not None:
            load_to = min(load_to, latest_ts)

        effective_cursor = cursor_ts
        if effective_cursor is None:
            effective_cursor = shift_unix_by_bars(self.start_anchor, self.step_timeframe, 1)

        frame = self._candles.load_dataframe(
            conn,
            self.symbol,
            self.step_timeframe,
            self.start_anchor,
            load_to,
            warmup_bars=warmup,
        )
        if latest_ts is None and not frame.empty:
            latest_ts = int(frame.iloc[-1]["ts"].timestamp())
        self.buffer.load(
            frame,
            self.indicators,
            start_anchor=self.start_anchor,
            cursor_ts=effective_cursor,
            pipeline=self._pipeline,
            latest_available_ts=latest_ts,
        )

    def reload_at(self, conn: psycopg.Connection, target_ts: int) -> None:
        """
        Reload buffer anchored at a seek target (far seek or indicator change).

        Args:
            conn: Database connection.
            target_ts: Seek target bar time (unix seconds).

        Raises:
            ValidationError: When ``target_ts`` is before ``start_anchor``.
        """
        if target_ts < self.start_anchor:
            raise ValidationError("SEEK_OUT_OF_RANGE", "seek target before start anchor")

        _, latest_ts, _ = self._candles.get_data_range(conn, self.symbol, self.step_timeframe)
        if latest_ts is not None and target_ts > latest_ts:
            target_ts = latest_ts

        warmup = self._pipeline.warmup_bars(self.indicators, self.step_timeframe)
        prefetch = settings.replay_prefetch_bars()
        load_to = advance_unix_by_bars(target_ts, self.step_timeframe, prefetch)
        if latest_ts is not None:
            load_to = min(load_to, latest_ts)

        frame = self._candles.load_dataframe(
            conn,
            self.symbol,
            self.step_timeframe,
            target_ts,
            load_to,
            warmup_bars=warmup,
        )

        self.buffer.load(
            frame,
            self.indicators,
            start_anchor=self.start_anchor,
            cursor_ts=target_ts,
            pipeline=self._pipeline,
            latest_available_ts=latest_ts,
            visible_from_ts=target_ts,
        )
        seek_idx = self.buffer.index_at_or_before(target_ts)
        if seek_idx >= 0:
            self.buffer.seek_to_index(seek_idx)
        self.state = "paused"

    def seek(self, conn: psycopg.Connection, to_ts: int) -> bool:
        """
        Seek cursor to a unix timestamp.

        Within trail + prefetch: moves cursor only (instant). Beyond that:
        reloads buffer at target and emits ``buffer_reset`` + ``snapshot``.

        Args:
            conn: Database connection (used when reload is required).
            to_ts: Target bar time (unix seconds).

        Returns:
            ``True`` when buffer was reloaded; ``False`` for in-buffer seek.

        Raises:
            ValidationError: When ``to_ts`` is before ``start_anchor``.
        """
        if to_ts < self.start_anchor:
            raise ValidationError("SEEK_OUT_OF_RANGE", "seek target before start anchor")

        target_idx = self.buffer.index_at_or_before(to_ts)
        trail = settings.replay_trail_bars()

        if target_idx >= 0:
            cursor_idx = self.buffer.cursor_idx
            if cursor_idx < 0:
                within_trail = True
            else:
                within_trail = target_idx >= cursor_idx - trail
            within_prefetch = target_idx <= self.buffer.prefetch_end_idx
            if within_trail and within_prefetch:
                self.buffer.seek_to_index(target_idx)
                self.state = "paused"
                return False

        self.reload_at(conn, to_ts)
        return True

    def maybe_extend(self, conn: psycopg.Connection) -> ReplayExtendResult:
        """
        Extend buffer forward when cursor nears the prefetch edge.

        Args:
            conn: Database connection for fetching additional candles.

        Returns:
            ``none`` — no extend needed.
            ``ready`` — extend completed; more bars available.
            ``completed`` — latest DB candle reached; no forward data left.
        """
        self._refresh_latest_available(conn)
        if not self.buffer.needs_extend(settings.replay_extend_threshold()):
            if self.buffer.at_latest():
                return "completed"
            return "none"

        last_ts = self.buffer.buffer_end_ts()
        if last_ts is None:
            return "none"

        _, latest_ts, _ = self._candles.get_data_range(conn, self.symbol, self.step_timeframe)
        if latest_ts is None or last_ts >= latest_ts:
            self.buffer.latest_available_ts = latest_ts
            return "ready"

        bar_seconds = TIMEFRAME_SECONDS[self.step_timeframe]
        fetch_from = last_ts + bar_seconds
        fetch_to = advance_unix_by_bars(
            last_ts,
            self.step_timeframe,
            settings.replay_prefetch_bars(),
        )
        fetch_to = min(fetch_to, latest_ts)

        new_frame = self._candles.load_dataframe(
            conn,
            self.symbol,
            self.step_timeframe,
            fetch_from,
            fetch_to,
        )
        if new_frame.empty:
            self.buffer.latest_available_ts = latest_ts
            return "ready"

        self.buffer.append_frame(new_frame, self.indicators, self._pipeline)
        self.buffer.latest_available_ts = latest_ts
        if self.buffer.at_latest() and not self.buffer.can_step():
            return "completed"
        return "ready"

    def step_batch(
        self,
        conn: psycopg.Connection,
        count: int | None = None,
    ) -> tuple[list[ReplayTick], ReplayExtendResult]:
        """
        Slice up to ``count`` ticks from the precomputed buffer.

        Each tick is O(1). Trims trail after each step; may trigger forward
        extend when cursor approaches prefetch edge.

        Args:
            conn: Database connection (for extend and latest-candle refresh).
            count: Max ticks to emit; defaults to ``REPLAY_TICK_BATCH_SIZE``.

        Returns:
            Tuple of (ticks, extend_status). ``extend_status`` is ``completed``
            when the latest stored candle has been reached.
        """
        batch_size = count if count is not None else settings.replay_tick_batch_size()
        ticks: list[ReplayTick] = []
        extend_status: ReplayExtendResult = "none"
        warmup = self._pipeline.warmup_bars(self.indicators, self.step_timeframe)

        self._refresh_latest_available(conn)

        if self.buffer.needs_extend(settings.replay_extend_threshold()):
            extend_status = self.maybe_extend(conn)

        for _ in range(batch_size):
            if not self.buffer.can_step():
                if self.buffer.at_latest():
                    self.state = "completed"
                    extend_status = "completed"
                break

            ticks.extend(self.buffer.slice_ticks(1))
            self.buffer.trim_trail(settings.replay_trail_bars(), warmup)

            if self.buffer.needs_extend(settings.replay_extend_threshold()):
                extend_status = self.maybe_extend(conn)

        if self.buffer.at_latest() and not self.buffer.can_step():
            self.state = "completed"
            if not ticks:
                extend_status = "completed"

        return ticks, extend_status

    def set_indicators(self, conn: psycopg.Connection, indicators: list[IndicatorSpec]) -> None:
        """
        Replace indicator specs and reload buffer at current cursor.

        Pauses playback and recomputes overlays over a fresh frame.

        Args:
            conn: Database connection.
            indicators: New indicator specifications.
        """
        self.indicators = indicators
        self.state = "paused"
        cursor = self.buffer.cursor_ts or shift_unix_by_bars(self.start_anchor, self.step_timeframe, 1)
        self.reload_at(conn, max(cursor, self.start_anchor))

    def set_speed(self, speed: float) -> None:
        """
        Update playback speed multiplier.

        The client derives interval as ``max(50, 1000 / speed)`` ms per bar.

        Args:
            speed: Must be > 0.

        Raises:
            ValidationError: When ``speed`` is not positive.
        """
        if speed <= 0:
            raise ValidationError("INVALID_SPEED", "speed must be > 0")
        self.speed = speed

    def tick_batch_payload(self, ticks: list[ReplayTick]) -> dict:
        """
        Build WS ``tick_batch`` event payload.

        Args:
            ticks: Ticks from ``step_batch``.

        Returns:
            JSON-serializable event dict with ``queueRemaining``.
        """
        return {
            "type": "tick_batch",
            "ticks": [
                {"bar": tick.bar.model_dump(), "indicators": tick.indicators}
                for tick in ticks
            ],
            "cursor": self.buffer.cursor_ts,
            "queueRemaining": self.buffer.queue_remaining(),
        }

    def snapshot_payload(self) -> dict:
        """
        Build WS ``snapshot`` event payload.

        Sent on connect, reconnect, seek reload, and indicator change.

        Returns:
            JSON-serializable event with trail bars and indicator series.
        """
        return {
            "type": "snapshot",
            "bars": [bar.model_dump() for bar in self.buffer.snapshot_bars()],
            "indicators": self.buffer.snapshot_indicators(),
            "cursor": self.buffer.cursor_ts,
            "startAnchor": self.start_anchor,
            "latestAvailable": self.buffer.latest_available_ts,
        }
