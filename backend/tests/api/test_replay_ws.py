"""
Tests for replay WebSocket v2.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from api.auth import create_access_token
from api.repositories.replay_repository import _row_to_session
from api.repositories.user_repository import UserRow
from api.schemas.replay import ReplaySessionCreate
from api.services.replay_session_store import ReplaySessionStore
from api.ws.replay import WS_REPLAY_NOT_FOUND, WS_SUPERSEDED, WS_UNAUTHORIZED

def _ws_url(session_id) -> str:
    token = create_access_token(user_id=_TEST_USER_ID, email="replay@example.com")
    return f"/ws/replay/{session_id}?token={token}"


def _auth_user() -> UserRow:
    now = datetime(2024, 1, 1, tzinfo=UTC)
    return UserRow(
        id=_TEST_USER_ID,
        name="Replay",
        email="replay@example.com",
        password_hash="x",
        created_at=now,
        updated_at=now,
    )



_TEST_USER_ID = uuid4()


def _session_row(
    session_id,
    *,
    start: int,
    cursor_ts: int,
    indicators: str = "[]",
    state: str = "paused",
    user_id=_TEST_USER_ID,
) -> tuple:
    now = datetime(2024, 1, 1, tzinfo=UTC)
    return (
        session_id,
        user_id,
        "BTC/USDT",
        "1d",
        "1d",
        start,
        cursor_ts,
        indicators,
        1.0,
        state,
        now,
        now,
    )


def _wire_replay_store(
    store: ReplaySessionStore,
    *,
    mock_connect: MagicMock,
    mock_get: MagicMock,
    mock_insert: MagicMock,
    sample_candles_df: pd.DataFrame,
    start: int | None = None,
) -> uuid4:
    """Create a cached session and attach the store to the global replay service."""
    if start is None:
        start = int(sample_candles_df["ts"].iloc[0].timestamp())

    def _insert(conn, **kwargs):
        return _row_to_session(_session_row(kwargs["session_id"], start=start, cursor_ts=start - 86400))

    mock_insert.side_effect = _insert

    conn = MagicMock()
    mock_connect.return_value.__enter__.return_value = conn
    mock_connect.return_value.__exit__.return_value = None

    engine = store.create(
        conn,
        ReplaySessionCreate(symbol="BTC/USDT", timeframe="1d", start=start, step_timeframe="1d"),
        user_id=_TEST_USER_ID,
    )
    session_id = engine.session_id
    mock_get.return_value = _row_to_session(
        _session_row(session_id, start=start, cursor_ts=start - 86400)
    )

    from api.services.replay_service import get_replay_service

    get_replay_service()._store = store
    return session_id


def _mock_create_store(sample_candles_df: pd.DataFrame) -> tuple[uuid4, ReplaySessionStore]:
    session_id = uuid4()
    now = datetime(2024, 1, 1, tzinfo=UTC)
    start = int(sample_candles_df["ts"].iloc[0].timestamp())
    row_tuple = (
        session_id,
        _TEST_USER_ID,
        "BTC/USDT",
        "1d",
        "1d",
        start,
        start - 86400,
        "[]",
        1.0,
        "paused",
        now,
        now,
    )
    return session_id, _row_to_session(row_tuple)


@patch("api.deps.user_from_ws_token")
@patch("api.ws.replay.connect")
@patch("api.services.replay_session_store.SymbolService.require_active_symbol")
@patch("api.services.replay_session_store.ReplayRepository.insert")
@patch("api.services.replay_session_store.ReplayRepository.get")
@patch("api.services.replay_engine.CandleService.load_dataframe")
@patch("api.services.replay_engine.CandleService.get_data_range")
def test_replay_websocket_step_emits_tick_batch(
    mock_range: MagicMock,
    mock_load: MagicMock,
    mock_get: MagicMock,
    mock_insert: MagicMock,
    _mock_symbol: MagicMock,
    mock_connect: MagicMock,
    mock_user_from_ws: MagicMock,
    client: TestClient,
    sample_candles_df: pd.DataFrame,
) -> None:
    """WS step command emits tick_batch and replay_state."""
    mock_user_from_ws.return_value = _auth_user()
    now = datetime(2024, 1, 1, tzinfo=UTC)
    start = int(sample_candles_df["ts"].iloc[0].timestamp())

    def _insert(conn, **kwargs):
        return _row_to_session(
            (
                kwargs["session_id"],
                _TEST_USER_ID,
                "BTC/USDT",
                "1d",
                "1d",
                start,
                start - 86400,
                "[]",
                1.0,
                "paused",
                now,
                now,
            )
        )

    mock_insert.side_effect = _insert
    mock_load.return_value = sample_candles_df
    latest = int(sample_candles_df["ts"].iloc[-1].timestamp())
    mock_range.return_value = (start, latest, 5)
    conn = MagicMock()
    mock_connect.return_value.__enter__.return_value = conn
    mock_connect.return_value.__exit__.return_value = None

    store = ReplaySessionStore()
    conn = MagicMock()
    engine = store.create(
        conn,
        ReplaySessionCreate(symbol="BTC/USDT", timeframe="1d", start=start, step_timeframe="1d"),
        user_id=_TEST_USER_ID,
    )
    session_id = engine.session_id
    mock_get.return_value = _row_to_session(
        (session_id, _TEST_USER_ID, "BTC/USDT", "1d", "1d", start, start - 86400, "[]", 1.0, "paused", now, now)
    )

    from api.services.replay_service import get_replay_service

    get_replay_service()._store = store

    with client.websocket_connect(_ws_url(session_id)) as websocket:
        state_msg = websocket.receive_json()
        assert state_msg["type"] == "replay_state"
        snapshot_msg = websocket.receive_json()
        assert snapshot_msg["type"] == "snapshot"

        websocket.send_json({"action": "step", "count": 1})
        batch_msg = websocket.receive_json()
        assert batch_msg["type"] == "tick_batch"
        assert len(batch_msg["ticks"]) == 1
        state_msg = websocket.receive_json()
        assert state_msg["type"] == "replay_state"
        assert state_msg["barIndex"] == 1


@patch("api.deps.user_from_ws_token")
@patch("api.ws.replay.connect")
@patch("api.services.replay_session_store.SymbolService.require_active_symbol")
@patch("api.services.replay_session_store.ReplayRepository.insert")
@patch("api.services.replay_session_store.ReplayRepository.get")
@patch("api.services.replay_engine.CandleService.load_dataframe")
@patch("api.services.replay_engine.CandleService.get_data_range")
def test_replay_websocket_autoplay_emits_tick_batch_on_connect(
    mock_range: MagicMock,
    mock_load: MagicMock,
    mock_get: MagicMock,
    mock_insert: MagicMock,
    _mock_symbol: MagicMock,
    mock_connect: MagicMock,
    mock_user_from_ws: MagicMock,
    client: TestClient,
    sample_candles_df: pd.DataFrame,
) -> None:
    """autoplay=True sends first tick_batch immediately after snapshot on WS connect."""
    mock_user_from_ws.return_value = _auth_user()
    now = datetime(2024, 1, 1, tzinfo=UTC)
    start = int(sample_candles_df["ts"].iloc[0].timestamp())

    def _insert(conn, **kwargs):
        return _row_to_session(
            (
                kwargs["session_id"],
                _TEST_USER_ID,
                "BTC/USDT",
                "1d",
                "1d",
                start,
                start - 86400,
                "[]",
                1.0,
                "paused",
                now,
                now,
            )
        )

    mock_insert.side_effect = _insert
    mock_load.return_value = sample_candles_df
    latest = int(sample_candles_df["ts"].iloc[-1].timestamp())
    mock_range.return_value = (start, latest, 5)
    conn = MagicMock()
    mock_connect.return_value.__enter__.return_value = conn
    mock_connect.return_value.__exit__.return_value = None

    store = ReplaySessionStore()
    engine = store.create(
        conn,
        ReplaySessionCreate(
            symbol="BTC/USDT",
            timeframe="1d",
            start=start,
            step_timeframe="1d",
            autoplay=True,
        ),
        user_id=_TEST_USER_ID,
    )
    session_id = engine.session_id
    mock_get.return_value = _row_to_session(
        (session_id, _TEST_USER_ID, "BTC/USDT", "1d", "1d", start, start - 86400, "[]", 1.0, "paused", now, now)
    )

    from api.services.replay_service import get_replay_service

    get_replay_service()._store = store

    with client.websocket_connect(_ws_url(session_id)) as websocket:
        assert websocket.receive_json()["type"] == "replay_state"
        assert websocket.receive_json()["type"] == "snapshot"
        playing_state = websocket.receive_json()
        assert playing_state["type"] == "replay_state"
        assert playing_state["state"] == "playing"
        batch_msg = websocket.receive_json()
        assert batch_msg["type"] == "tick_batch"
        assert len(batch_msg["ticks"]) >= 1


@patch("api.deps.user_from_ws_token")
@patch("api.ws.replay.connect")
@patch("api.services.replay_session_store.ReplayRepository.get")
def test_replay_websocket_unknown_session_closes_4404(
    mock_get: MagicMock,
    mock_connect: MagicMock,
    mock_user_from_ws: MagicMock,
    client: TestClient,
) -> None:
    """Unknown session closes the WebSocket with code 4404 before any replay events."""
    mock_user_from_ws.return_value = _auth_user()
    session_id = uuid4()
    mock_get.return_value = None
    conn = MagicMock()
    mock_connect.return_value.__enter__.return_value = conn
    mock_connect.return_value.__exit__.return_value = None

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(_ws_url(session_id)) as websocket:
            websocket.receive_json()

    assert exc_info.value.code == WS_REPLAY_NOT_FOUND


def test_replay_ws_close_codes_auth_vs_superseded_are_distinct() -> None:
    """G-002 / G2-003: auth and superseded must not share a close code."""
    import inspect

    import api.ws.replay as replay_ws

    assert WS_UNAUTHORIZED == 4401
    assert WS_SUPERSEDED == 4402
    assert WS_REPLAY_NOT_FOUND == 4404
    assert WS_UNAUTHORIZED != WS_SUPERSEDED
    # Handler must close superseded tabs with WS_SUPERSEDED (not UNAUTHORIZED).
    src = inspect.getsource(replay_ws.replay_websocket)
    assert "prior.close(code=WS_SUPERSEDED" in src
    assert "close(code=WS_UNAUTHORIZED" in src


@patch("api.settings.replay_tick_batch_size", return_value=2)
@patch("api.deps.user_from_ws_token")
@patch("api.ws.replay.connect")
@patch("api.services.replay_session_store.SymbolService.require_active_symbol")
@patch("api.services.replay_session_store.ReplayRepository.insert")
@patch("api.services.replay_session_store.ReplayRepository.get")
@patch("api.services.replay_engine.CandleService.load_dataframe")
@patch("api.services.replay_engine.CandleService.get_data_range")
def test_replay_websocket_refill_emits_tick_batch(
    mock_range: MagicMock,
    mock_load: MagicMock,
    mock_get: MagicMock,
    mock_insert: MagicMock,
    _mock_symbol: MagicMock,
    mock_connect: MagicMock,
    mock_user_from_ws: MagicMock,
    _mock_batch_size: MagicMock,
    client: TestClient,
    sample_candles_df: pd.DataFrame,
) -> None:
    """refill requests a full tick_batch for client queue top-up."""
    mock_user_from_ws.return_value = _auth_user()
    mock_insert.side_effect = lambda conn, **kwargs: _row_to_session(
        _session_row(
            kwargs["session_id"],
            start=int(sample_candles_df["ts"].iloc[0].timestamp()),
            cursor_ts=int(sample_candles_df["ts"].iloc[0].timestamp()) - 86400,
        )
    )
    mock_load.return_value = sample_candles_df
    start = int(sample_candles_df["ts"].iloc[0].timestamp())
    latest = int(sample_candles_df["ts"].iloc[-1].timestamp())
    mock_range.return_value = (start, latest, len(sample_candles_df))

    store = ReplaySessionStore()
    session_id = _wire_replay_store(
        store,
        mock_connect=mock_connect,
        mock_get=mock_get,
        mock_insert=mock_insert,
        sample_candles_df=sample_candles_df,
        start=start,
    )

    with client.websocket_connect(_ws_url(session_id)) as websocket:
        assert websocket.receive_json()["type"] == "replay_state"
        assert websocket.receive_json()["type"] == "snapshot"

        websocket.send_json({"action": "refill"})
        batch_msg = websocket.receive_json()
        assert batch_msg["type"] == "tick_batch"
        assert len(batch_msg["ticks"]) >= 1
        assert "queueRemaining" in batch_msg
        assert websocket.receive_json()["type"] == "replay_state"


@patch("api.settings.replay_session_idle_minutes", return_value=0)
@patch("api.deps.user_from_ws_token")
@patch("api.ws.replay.connect")
@patch("api.services.replay_session_store.SymbolService.require_active_symbol")
@patch("api.services.replay_session_store.ReplayRepository.insert")
@patch("api.services.replay_session_store.ReplayRepository.get")
@patch("api.services.replay_session_store.ReplayRepository.update_checkpoint")
@patch("api.services.replay_engine.CandleService.load_dataframe")
@patch("api.services.replay_engine.CandleService.get_data_range")
def test_replay_websocket_reconnect_after_idle_eviction(
    mock_range: MagicMock,
    mock_load: MagicMock,
    mock_checkpoint: MagicMock,
    mock_get: MagicMock,
    mock_insert: MagicMock,
    _mock_symbol: MagicMock,
    mock_connect: MagicMock,
    mock_user_from_ws: MagicMock,
    _mock_idle: MagicMock,
    client: TestClient,
    sample_candles_df: pd.DataFrame,
) -> None:
    """Idle eviction drops the hot buffer; reconnect rebuilds snapshot from DB cursor."""
    mock_user_from_ws.return_value = _auth_user()
    start = int(sample_candles_df["ts"].iloc[0].timestamp())
    latest = int(sample_candles_df["ts"].iloc[-1].timestamp())
    mock_load.return_value = sample_candles_df
    mock_range.return_value = (start, latest, len(sample_candles_df))

    def _insert(conn, **kwargs):
        return _row_to_session(
            _session_row(kwargs["session_id"], start=start, cursor_ts=start - 86400)
        )

    mock_insert.side_effect = _insert

    store = ReplaySessionStore()
    conn = MagicMock()
    mock_connect.return_value.__enter__.return_value = conn
    mock_connect.return_value.__exit__.return_value = None

    engine = store.create(
        conn,
        ReplaySessionCreate(symbol="BTC/USDT", timeframe="1d", start=start, step_timeframe="1d"),
        user_id=_TEST_USER_ID,
    )
    session_id = engine.session_id
    engine.step_batch(conn, count=2)
    cursor_ts = engine.cursor_ts()
    assert cursor_ts is not None

    mock_checkpoint.return_value = _row_to_session(
        _session_row(session_id, start=start, cursor_ts=cursor_ts, state="paused")
    )
    store.checkpoint(conn, session_id, force=True)
    store._cache[session_id].last_access = 0.0
    store._evict_idle()
    assert session_id not in store._cache

    mock_get.return_value = _row_to_session(
        _session_row(session_id, start=start, cursor_ts=cursor_ts, state="paused")
    )

    from api.services.replay_service import get_replay_service

    get_replay_service()._store = store

    with client.websocket_connect(_ws_url(session_id)) as websocket:
        state_msg = websocket.receive_json()
        assert state_msg["type"] == "replay_state"
        assert state_msg["barIndex"] == 2
        snapshot_msg = websocket.receive_json()
        assert snapshot_msg["type"] == "snapshot"
        assert len(snapshot_msg["bars"]) == 2


@patch("api.settings.replay_extend_threshold", return_value=1)
@patch("api.settings.replay_prefetch_bars", return_value=2)
@patch("api.deps.user_from_ws_token")
@patch("api.ws.replay.connect")
@patch("api.services.replay_session_store.SymbolService.require_active_symbol")
@patch("api.services.replay_session_store.ReplayRepository.insert")
@patch("api.services.replay_session_store.ReplayRepository.get")
@patch("api.services.replay_engine.CandleService.load_dataframe")
@patch("api.services.replay_engine.CandleService.get_data_range")
def test_replay_websocket_forward_extend_emits_buffer_events(
    mock_range: MagicMock,
    mock_load: MagicMock,
    mock_get: MagicMock,
    mock_insert: MagicMock,
    _mock_symbol: MagicMock,
    mock_connect: MagicMock,
    mock_user_from_ws: MagicMock,
    _mock_prefetch: MagicMock,
    _mock_threshold: MagicMock,
    client: TestClient,
) -> None:
    """When cursor reaches the prefetch edge, server emits buffer_loading then buffer_ready."""
    mock_user_from_ws.return_value = _auth_user()
    full = pd.DataFrame(
        {
            "ts": pd.date_range("2024-01-01", periods=8, freq="D", tz="UTC"),
            "open": [99.0] * 8,
            "high": [102.0] * 8,
            "low": [97.0] * 8,
            "close": [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0],
            "volume": [1000.0] * 8,
        }
    )
    start = int(full["ts"].iloc[0].timestamp())
    latest = int(full["ts"].iloc[-1].timestamp())
    mock_range.return_value = (start, latest, len(full))

    def _slice_frame(_conn, _symbol, _tf, from_ts: int, to_ts: int, warmup_bars: int = 0) -> pd.DataFrame:
        rows = [
            idx
            for idx, ts in enumerate(full["ts"])
            if from_ts <= int(ts.timestamp()) <= to_ts
        ]
        if not rows:
            return full.iloc[0:0].copy()
        return full.iloc[rows[0] : rows[-1] + 1].copy()

    mock_load.side_effect = _slice_frame

    def _insert(conn, **kwargs):
        return _row_to_session(
            _session_row(kwargs["session_id"], start=start, cursor_ts=start - 86400)
        )

    mock_insert.side_effect = _insert

    store = ReplaySessionStore()
    conn = MagicMock()
    mock_connect.return_value.__enter__.return_value = conn
    mock_connect.return_value.__exit__.return_value = None

    engine = store.create(
        conn,
        ReplaySessionCreate(symbol="BTC/USDT", timeframe="1d", start=start, step_timeframe="1d"),
        user_id=_TEST_USER_ID,
    )
    session_id = engine.session_id
    engine.buffer.cursor_idx = 1
    mock_get.return_value = _row_to_session(
        _session_row(session_id, start=start, cursor_ts=engine.cursor_ts() or start, state="paused")
    )

    from api.services.replay_service import get_replay_service

    get_replay_service()._store = store

    with client.websocket_connect(_ws_url(session_id)) as websocket:
        assert websocket.receive_json()["type"] == "replay_state"
        assert websocket.receive_json()["type"] == "snapshot"

        websocket.send_json({"action": "step", "count": 1})
        assert websocket.receive_json()["type"] == "buffer_loading"
        assert websocket.receive_json()["type"] == "tick_batch"
        ready_msg = websocket.receive_json()
        assert ready_msg["type"] == "buffer_ready"
        assert ready_msg["latestAvailable"] == latest
        assert websocket.receive_json()["type"] == "replay_state"
