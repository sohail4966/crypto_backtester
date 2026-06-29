"""
DB-backed replay session store with in-memory hot buffer cache.

Persists session metadata and cursor checkpoints in ``app.replay_sessions``.
The ``ReplayBuffer`` is cached in memory and rebuilt from candles on cache miss
or reconnect.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from uuid import UUID, uuid4

import psycopg

from api import settings
from api.exceptions import NotFoundError, ValidationError
from api.repositories.replay_repository import ReplayRepository, ReplaySessionRow, ReplayState
from api.schemas.indicators import IndicatorSpec
from api.schemas.replay import ReplaySessionCreate
from api.services.candle_service import CandleService
from api.services.replay_engine import ReplayEngine
from api.services.symbol_service import SymbolService
from api.services.timeframes import shift_unix_by_bars, validate_timeframe


@dataclass
class CachedReplay:
    """
    In-memory cache entry for an active replay session.

    Attributes:
        engine: Live replay engine with hot buffer.
        last_access: Unix time of last API/WS access (for idle eviction).
        last_checkpoint: Unix time of last DB cursor flush.
        autoplay: One-shot flag to send first tick batch on WS connect.
    """

    engine: ReplayEngine
    last_access: float
    last_checkpoint: float
    autoplay: bool = False


class ReplaySessionStore:
    """
    Persist replay metadata in Postgres; cache ``ReplayEngine`` in memory.

    Idle sessions are evicted from cache after ``REPLAY_SESSION_IDLE_MINUTES``;
    the DB row remains for resume.
    """

    def __init__(
        self,
        repository: ReplayRepository | None = None,
        candle_service: CandleService | None = None,
        symbol_service: SymbolService | None = None,
    ) -> None:
        """
        Args:
            repository: Replay session DB access (default: new instance).
            candle_service: Candle loader for buffer rebuild (default: new).
            symbol_service: Symbol validation (default: new instance).
        """
        self._repo = repository or ReplayRepository()
        self._candles = candle_service or CandleService()
        self._symbols = symbol_service or SymbolService()
        self._cache: dict[UUID, CachedReplay] = {}

    def _evict_idle(self) -> None:
        """Remove cache entries idle longer than ``REPLAY_SESSION_IDLE_MINUTES``."""
        idle_seconds = settings.replay_session_idle_minutes() * 60
        now = time.time()
        expired = [
            sid
            for sid, cached in self._cache.items()
            if now - cached.last_access > idle_seconds
        ]
        for sid in expired:
            del self._cache[sid]

    def _touch(self, cached: CachedReplay) -> None:
        """Update last-access time to prevent idle eviction."""
        cached.last_access = time.time()

    def create(self, conn: psycopg.Connection, body: ReplaySessionCreate) -> ReplayEngine:
        """
        Create a new open-ended replay session.

        Inserts a DB row, loads the initial buffer, and caches the engine.
        Sessions start paused; WS ``play`` or ``autoplay`` begins stepping.

        Args:
            conn: Database connection (committed before return).
            body: Session create request.

        Returns:
            Engine ready for WebSocket control.

        Raises:
            ValidationError: Invalid timeframe or unknown symbol.
        """
        self._evict_idle()
        self._symbols.require_active_symbol(conn, body.symbol)
        step_tf = body.step_timeframe or body.timeframe
        try:
            validate_timeframe(body.timeframe)
            validate_timeframe(step_tf)
        except ValueError as exc:
            raise ValidationError("INVALID_TIMEFRAME", str(exc)) from exc

        session_id = uuid4()
        cursor_ts = shift_unix_by_bars(body.start, step_tf, 1)
        state: ReplayState = "paused"

        row = self._repo.insert(
            conn,
            session_id=session_id,
            symbol=body.symbol,
            timeframe=body.timeframe,
            step_timeframe=step_tf,
            start_anchor=body.start,
            cursor_ts=cursor_ts,
            indicators=list(body.indicators),
            speed=body.speed,
            state=state,
        )
        conn.commit()

        engine = ReplayEngine.from_row(row, candle_service=self._candles)
        engine.load_buffer(conn, cursor_ts=cursor_ts)
        now = time.time()
        self._cache[session_id] = CachedReplay(
            engine=engine,
            last_access=now,
            last_checkpoint=now,
            autoplay=body.autoplay,
        )
        return engine

    def get_engine(self, conn: psycopg.Connection, session_id: UUID) -> ReplayEngine:
        """
        Return the cached engine or rebuild buffer from DB on cache miss.

        Args:
            conn: Database connection (for buffer rebuild when evicted).
            session_id: Session UUID.

        Returns:
            Engine with buffer loaded at saved cursor.

        Raises:
            NotFoundError: When session row does not exist.
        """
        self._evict_idle()
        cached = self._cache.get(session_id)
        if cached is not None:
            self._touch(cached)
            return cached.engine

        row = self._repo.get(conn, session_id)
        if row is None:
            raise NotFoundError("REPLAY_NOT_FOUND", f"Unknown replay session: {session_id}")

        engine = ReplayEngine.from_row(row, candle_service=self._candles)
        engine.load_buffer(conn, cursor_ts=row.cursor_ts)
        now = time.time()
        self._cache[session_id] = CachedReplay(
            engine=engine,
            last_access=now,
            last_checkpoint=now,
            autoplay=False,
        )
        return engine

    def consume_autoplay(self, session_id: UUID) -> bool:
        """
        Return and clear the one-shot autoplay flag for WS connect.

        When ``True``, the WebSocket handler sends the first ``tick_batch``
        immediately after ``snapshot``.

        Args:
            session_id: Session UUID.

        Returns:
            Whether autoplay was requested at session create.
        """
        cached = self._cache.get(session_id)
        if cached is None or not cached.autoplay:
            return False
        cached.autoplay = False
        return True

    def get_row(self, conn: psycopg.Connection, session_id: UUID) -> ReplaySessionRow:
        """
        Fetch session metadata from the database (no buffer).

        Args:
            conn: Database connection.
            session_id: Session UUID.

        Returns:
            Persisted session row.

        Raises:
            NotFoundError: When session does not exist.
        """
        row = self._repo.get(conn, session_id)
        if row is None:
            raise NotFoundError("REPLAY_NOT_FOUND", f"Unknown replay session: {session_id}")
        return row

    def checkpoint(self, conn: psycopg.Connection, session_id: UUID, *, force: bool = False) -> None:
        """
        Flush cursor position and state to the database.

        Skips write unless ``force`` is set or ``REPLAY_CHECKPOINT_INTERVAL_SEC``
        has elapsed since the last checkpoint.

        Args:
            conn: Database connection (committed on update).
            session_id: Session UUID.
            force: Write immediately (pause, disconnect, seek).
        """
        cached = self._cache.get(session_id)
        if cached is None:
            return
        now = time.time()
        interval = settings.replay_checkpoint_interval_sec()
        if not force and now - cached.last_checkpoint < interval:
            return
        engine = cached.engine
        cursor_ts = engine.cursor_ts() or shift_unix_by_bars(
            engine.start_anchor,
            engine.step_timeframe,
            1,
        )
        updated = self._repo.update_checkpoint(
            conn,
            session_id,
            cursor_ts=cursor_ts,
            speed=engine.speed,
            state=engine.state,
        )
        if updated is not None:
            conn.commit()
            cached.last_checkpoint = now

    def update_indicators(
        self,
        conn: psycopg.Connection,
        session_id: UUID,
        indicators: list[IndicatorSpec],
    ) -> ReplayEngine:
        """
        Persist new indicator specs and reload the in-memory buffer.

        Args:
            conn: Database connection.
            session_id: Session UUID.
            indicators: Replacement indicator specifications.

        Returns:
            Engine with recomputed overlays.

        Raises:
            NotFoundError: When session does not exist.
        """
        engine = self.get_engine(conn, session_id)
        updated = self._repo.update_indicators(conn, session_id, indicators)
        if updated is None:
            raise NotFoundError("REPLAY_NOT_FOUND", f"Unknown replay session: {session_id}")
        conn.commit()
        engine.set_indicators(conn, indicators)
        cached = self._cache.get(session_id)
        if cached is not None:
            self._touch(cached)
        return engine

    def delete(self, conn: psycopg.Connection, session_id: UUID) -> None:
        """
        Delete session from database and evict from cache.

        Args:
            conn: Database connection (committed before return).
            session_id: Session UUID.
        """
        self._repo.delete(conn, session_id)
        conn.commit()
        self._cache.pop(session_id, None)

    def clear_cache(self) -> None:
        """Clear in-memory cache (test helper)."""
        self._cache.clear()
