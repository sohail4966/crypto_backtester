"""Tests for replay session repository and store."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pandas as pd

from api.repositories.replay_repository import ReplayRepository, _row_to_session
from api.schemas.indicators import IndicatorSpec
from api.schemas.replay import ReplaySessionCreate
from api.services.replay_session_store import CachedReplay, ReplaySessionStore


def _session_row_tuple(session_id):
    now = datetime(2024, 1, 1, tzinfo=UTC)
    indicators = json.dumps([{"key": "RSI", "params": {"period": 14}}])
    return (
        session_id,
        "BTC/USDT",
        "1h",
        "1h",
        1704067200,
        1704063600,
        indicators,
        1.0,
        "paused",
        now,
        now,
    )


def test_repository_insert_executes_sql() -> None:
    """Insert uses INSERT_REPLAY_SESSION query."""
    conn = MagicMock()
    cursor = MagicMock()
    session_id = uuid4()
    cursor.fetchone.return_value = _session_row_tuple(session_id)
    conn.cursor.return_value.__enter__.return_value = cursor

    row = ReplayRepository().insert(
        conn,
        session_id=session_id,
        symbol="BTC/USDT",
        timeframe="1h",
        step_timeframe="1h",
        start_anchor=1704067200,
        cursor_ts=1704063600,
        indicators=[IndicatorSpec(key="RSI", params={"period": 14})],
        speed=1.0,
        state="paused",
    )

    assert row.session_id == session_id
    assert row.indicators[0].key == "RSI"
    cursor.execute.assert_called_once()


def test_store_checkpoint_updates_repository() -> None:
    """Checkpoint flushes cursor to repository when forced."""
    from api.services.replay_engine import ReplayEngine

    conn = MagicMock()
    repo = MagicMock()
    store = ReplaySessionStore(repository=repo)
    session_id = uuid4()
    engine = ReplayEngine(
        session_id=session_id,
        symbol="BTC/USDT",
        timeframe="1h",
        step_timeframe="1h",
        start_anchor=1704067200,
        speed=1.0,
        state="paused",
        indicators=[],
    )
    store._cache[session_id] = CachedReplay(engine=engine, last_access=0.0, last_checkpoint=0.0)

    store.checkpoint(conn, session_id, force=True)
    repo.update_checkpoint.assert_called_once()


@patch("api.services.replay_session_store.SymbolService.require_active_symbol")
@patch("api.services.replay_session_store.ReplayRepository.insert")
@patch("api.services.replay_engine.CandleService.load_dataframe")
@patch("api.services.replay_engine.CandleService.get_data_range")
def test_store_create_caches_engine(
    mock_range: MagicMock,
    mock_load: MagicMock,
    mock_insert: MagicMock,
    _mock_symbol: MagicMock,
) -> None:
    """Create inserts DB row and caches engine with buffer."""
    def _insert(conn, **kwargs):
        return _row_to_session(_session_row_tuple(kwargs["session_id"]))

    mock_insert.side_effect = _insert
    frame = pd.DataFrame(
        {
            "ts": pd.date_range("2024-01-01", periods=5, freq="D", tz="UTC"),
            "open": [99.0] * 5,
            "high": [102.0] * 5,
            "low": [97.0] * 5,
            "close": [100.0, 102.0, 101.0, 105.0, 108.0],
            "volume": [1000.0] * 5,
        }
    )
    mock_load.return_value = frame
    latest = int(frame["ts"].iloc[-1].timestamp())
    mock_range.return_value = (int(frame["ts"].iloc[0].timestamp()), latest, 5)

    store = ReplaySessionStore()
    conn = MagicMock()
    engine = store.create(
        conn,
        ReplaySessionCreate(symbol="BTC/USDT", timeframe="1d", start=1704067200, step_timeframe="1d"),
    )
    assert engine.session_id in store._cache
