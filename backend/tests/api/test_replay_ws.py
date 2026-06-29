"""
Tests for replay WebSocket v2.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pandas as pd
from fastapi.testclient import TestClient

from api.repositories.replay_repository import _row_to_session
from api.schemas.replay import ReplaySessionCreate
from api.services.replay_session_store import ReplaySessionStore


def _mock_create_store(sample_candles_df: pd.DataFrame) -> tuple[uuid4, ReplaySessionStore]:
    session_id = uuid4()
    now = datetime(2024, 1, 1, tzinfo=UTC)
    start = int(sample_candles_df["ts"].iloc[0].timestamp())
    row_tuple = (
        session_id,
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
    client: TestClient,
    sample_candles_df: pd.DataFrame,
) -> None:
    """WS step command emits tick_batch and replay_state."""
    now = datetime(2024, 1, 1, tzinfo=UTC)
    start = int(sample_candles_df["ts"].iloc[0].timestamp())

    def _insert(conn, **kwargs):
        return _row_to_session(
            (
                kwargs["session_id"],
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
    )
    session_id = engine.session_id
    mock_get.return_value = _row_to_session(
        (session_id, "BTC/USDT", "1d", "1d", start, start - 86400, "[]", 1.0, "paused", now, now)
    )

    from api.services.replay_service import get_replay_service

    get_replay_service()._store = store

    with client.websocket_connect(f"/ws/replay/{session_id}") as websocket:
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
    client: TestClient,
    sample_candles_df: pd.DataFrame,
) -> None:
    """autoplay=True sends first tick_batch immediately after snapshot on WS connect."""
    now = datetime(2024, 1, 1, tzinfo=UTC)
    start = int(sample_candles_df["ts"].iloc[0].timestamp())

    def _insert(conn, **kwargs):
        return _row_to_session(
            (
                kwargs["session_id"],
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
    )
    session_id = engine.session_id
    mock_get.return_value = _row_to_session(
        (session_id, "BTC/USDT", "1d", "1d", start, start - 86400, "[]", 1.0, "paused", now, now)
    )

    from api.services.replay_service import get_replay_service

    get_replay_service()._store = store

    with client.websocket_connect(f"/ws/replay/{session_id}") as websocket:
        assert websocket.receive_json()["type"] == "replay_state"
        assert websocket.receive_json()["type"] == "snapshot"
        playing_state = websocket.receive_json()
        assert playing_state["type"] == "replay_state"
        assert playing_state["state"] == "playing"
        batch_msg = websocket.receive_json()
        assert batch_msg["type"] == "tick_batch"
        assert len(batch_msg["ticks"]) >= 1
