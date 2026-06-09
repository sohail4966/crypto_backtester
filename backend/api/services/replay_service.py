"""
In-memory bar replay session manager.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Literal
from uuid import UUID, uuid4

import pandas as pd
import psycopg

from api import settings
from api.exceptions import NotFoundError, ValidationError
from api.schemas.candles import Bar
from api.schemas.indicators import IndicatorSeries, IndicatorSpec
from api.schemas.replay import ReplaySessionCreate, ReplayStateResponse
from api.services.candle_service import CandleService, _ts_to_unix
from api.services.indicator_service import IndicatorService, max_warmup_bars
from api.services.timeframes import validate_timeframe
from indicators.warmup import frame_window_indices


ReplayState = Literal["idle", "playing", "paused", "completed"]


@dataclass
class ReplaySession:
    """Mutable in-memory replay session."""

    session_id: UUID
    symbol: str
    timeframe: str
    step_timeframe: str
    start: int
    end: int
    speed: float
    state: ReplayState
    cursor_index: int
    bars: list[Bar] = field(default_factory=list)
    frame: pd.DataFrame = field(default_factory=pd.DataFrame)
    window_start_index: int = 0
    indicators: list[IndicatorSpec] = field(default_factory=list)
    last_access: float = field(default_factory=time.time)


class ReplayService:
    """Create and control in-memory replay sessions."""

    def __init__(
        self,
        candle_service: CandleService | None = None,
        indicator_service: IndicatorService | None = None,
    ) -> None:
        self._candles = candle_service or CandleService()
        self._indicators = indicator_service or IndicatorService()
        self._sessions: dict[UUID, ReplaySession] = {}

    def _evict_idle(self) -> None:
        """Remove sessions idle longer than configured timeout."""
        idle_seconds = settings.replay_session_idle_minutes() * 60
        now = time.time()
        expired = [
            sid
            for sid, session in self._sessions.items()
            if now - session.last_access > idle_seconds
        ]
        for sid in expired:
            del self._sessions[sid]

    def _touch(self, session: ReplaySession) -> None:
        """Update last access time."""
        session.last_access = time.time()

    def _visible_bars(
        self,
        df: pd.DataFrame,
        from_ts: int,
        to_ts: int,
    ) -> tuple[list[Bar], int]:
        """Return replay-visible bars and their start index in ``df``."""
        if df.empty:
            return [], 0
        unix_times = [_ts_to_unix(ts) for ts in df["ts"]]
        window_start, window_end = frame_window_indices(unix_times, from_ts, to_ts)
        if window_start < 0:
            return [], 0
        visible = df.iloc[window_start : window_end + 1]
        return self._dataframe_to_bars(visible), window_start

    def _dataframe_to_bars(self, df: pd.DataFrame) -> list[Bar]:
        """Convert OHLCV DataFrame to chart bars."""
        if df.empty:
            return []
        return [
            Bar(
                time=_ts_to_unix(row.ts),
                open=float(row.open),
                high=float(row.high),
                low=float(row.low),
                close=float(row.close),
                volume=float(row.volume),
            )
            for row in df.itertuples(index=False)
        ]

    def create_session(
        self,
        conn: psycopg.Connection,
        body: ReplaySessionCreate,
    ) -> ReplaySession:
        """
        Create a replay session and preload step candles.

        Args:
            conn: Database connection.
            body: Session configuration.

        Returns:
            New ReplaySession stored in memory.
        """
        self._evict_idle()
        step_tf = body.step_timeframe or body.timeframe
        try:
            validate_timeframe(body.timeframe)
            validate_timeframe(step_tf)
        except ValueError as exc:
            raise ValidationError("INVALID_TIMEFRAME", str(exc)) from exc

        if body.start > body.end:
            raise ValidationError("INVALID_RANGE", "start must be <= end")

        warmup = max_warmup_bars(body.indicators, step_tf)
        df = self._candles.load_dataframe(
            conn,
            body.symbol,
            step_tf,
            body.start,
            body.end,
            warmup_bars=warmup,
        )
        bars, window_start = self._visible_bars(df, body.start, body.end)
        max_bars = settings.replay_max_window_bars()
        if len(bars) > max_bars:
            raise ValidationError(
                "REPLAY_WINDOW_TOO_LARGE",
                f"Replay window exceeds {max_bars} bars",
            )

        session = ReplaySession(
            session_id=uuid4(),
            symbol=body.symbol,
            timeframe=body.timeframe,
            step_timeframe=step_tf,
            start=body.start,
            end=body.end,
            speed=body.speed,
            state="paused" if not body.autoplay else "playing",
            cursor_index=-1,
            bars=bars,
            frame=df,
            window_start_index=window_start,
            indicators=list(body.indicators),
        )
        self._sessions[session.session_id] = session
        return session

    def get_session(self, session_id: UUID) -> ReplaySession:
        """Return session or raise NotFoundError."""
        self._evict_idle()
        session = self._sessions.get(session_id)
        if session is None:
            raise NotFoundError("REPLAY_NOT_FOUND", f"Unknown replay session: {session_id}")
        self._touch(session)
        return session

    def delete_session(self, session_id: UUID) -> None:
        """Remove session from memory."""
        if session_id in self._sessions:
            del self._sessions[session_id]

    def to_state_response(self, session: ReplaySession) -> ReplayStateResponse:
        """Build REST/WS state snapshot."""
        cursor_time = None
        if 0 <= session.cursor_index < len(session.bars):
            cursor_time = session.bars[session.cursor_index].time
        return ReplayStateResponse(
            session_id=session.session_id,
            symbol=session.symbol,
            timeframe=session.timeframe,
            step_timeframe=session.step_timeframe,
            start=session.start,
            end=session.end,
            cursor=cursor_time,
            state=session.state,
            speed=session.speed,
            bar_index=max(session.cursor_index, 0),
            total_bars=len(session.bars),
            indicators=session.indicators,
        )

    def step(
        self,
        session: ReplaySession,
        count: int = 1,
    ) -> tuple[Bar | None, list[IndicatorSeries], bool]:
        """
        Advance replay cursor and return bar + indicators.

        Returns:
            Tuple of (bar, indicator series, completed flag).
        """
        if not session.bars:
            session.state = "completed"
            return None, [], True

        completed = False
        bar: Bar | None = None
        for _ in range(max(1, count)):
            if session.cursor_index >= len(session.bars) - 1:
                session.state = "completed"
                completed = True
                break
            session.cursor_index += 1
            bar = session.bars[session.cursor_index]

        if bar is None:
            return None, [], completed

        prefix_end = session.window_start_index + session.cursor_index
        indicators = self._indicators.compute_on_dataframe(
            session.frame,
            session.indicators,
            prefix_end=prefix_end,
            output_from_ts=session.start,
            output_to_ts=session.end,
        )
        self._touch(session)
        return bar, indicators, completed

    def seek(self, session: ReplaySession, to_ts: int) -> None:
        """Jump cursor to the bar at or before to_ts."""
        index = -1
        for idx, bar in enumerate(session.bars):
            if bar.time <= to_ts:
                index = idx
            else:
                break
        if index < 0:
            raise ValidationError("SEEK_OUT_OF_RANGE", "seek target before replay window")
        session.cursor_index = index
        session.state = "paused"
        self._touch(session)

    def set_speed(self, session: ReplaySession, speed: float) -> None:
        """Update autoplay speed."""
        if speed <= 0:
            raise ValidationError("INVALID_SPEED", "speed must be > 0")
        session.speed = speed
        self._touch(session)

    def set_step_timeframe(
        self,
        conn: psycopg.Connection,
        session: ReplaySession,
        step_timeframe: str,
    ) -> None:
        """Reload step bars for a new timeframe."""
        try:
            validate_timeframe(step_timeframe)
        except ValueError as exc:
            raise ValidationError("INVALID_TIMEFRAME", str(exc)) from exc
        warmup = max_warmup_bars(session.indicators, step_timeframe)
        df = self._candles.load_dataframe(
            conn,
            session.symbol,
            step_timeframe,
            session.start,
            session.end,
            warmup_bars=warmup,
        )
        bars, window_start = self._visible_bars(df, session.start, session.end)
        max_bars = settings.replay_max_window_bars()
        if len(bars) > max_bars:
            raise ValidationError(
                "REPLAY_WINDOW_TOO_LARGE",
                f"Replay window exceeds {max_bars} bars",
            )
        session.step_timeframe = step_timeframe
        session.frame = df
        session.window_start_index = window_start
        session.bars = bars
        session.cursor_index = min(session.cursor_index, len(bars) - 1)
        session.state = "paused"
        self._touch(session)

    def set_indicators(self, session: ReplaySession, indicators: list[IndicatorSpec]) -> None:
        """Replace indicator set for future steps."""
        session.indicators = indicators
        self._touch(session)


_replay_service: ReplayService | None = None


def get_replay_service() -> ReplayService:
    """Return process-wide replay session store."""
    global _replay_service
    if _replay_service is None:
        _replay_service = ReplayService()
    return _replay_service
