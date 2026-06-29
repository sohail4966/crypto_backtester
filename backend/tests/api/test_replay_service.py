"""
Tests for replay engine tick batches and indicator precompute.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pandas as pd

from api.repositories.replay_repository import ReplaySessionRow
from api.schemas.indicators import IndicatorSpec
from api.schemas.replay import ReplaySessionCreate
from api.services.replay_session_store import ReplaySessionStore


def _row(session_id) -> ReplaySessionRow:
    from datetime import UTC, datetime

    return ReplaySessionRow(
        session_id=session_id,
        symbol="BTC/USDT",
        timeframe="1d",
        step_timeframe="1d",
        start_anchor=int(pd.Timestamp("2024-01-01", tz="UTC").timestamp()),
        cursor_ts=int(pd.Timestamp("2023-12-31", tz="UTC").timestamp()),
        indicators=[IndicatorSpec(key="SMA", params={"period": 2})],
        speed=1.0,
        state="paused",
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
    )


@patch("api.services.replay_session_store.SymbolService.require_active_symbol")
@patch("api.services.replay_session_store.ReplayRepository.insert")
@patch("api.services.replay_engine.CandleService.load_dataframe")
@patch("api.services.replay_engine.CandleService.get_data_range")
def test_replay_step_emits_tick_batch_indicators(
    mock_range: MagicMock,
    mock_load: MagicMock,
    mock_insert: MagicMock,
    _mock_symbol: MagicMock,
    sample_candles_df: pd.DataFrame,
) -> None:
    """Tick batch indicators come from precomputed buffer, not prefix recompute."""
    session_id = uuid4()
    from api.repositories.replay_repository import _row_to_session
    import json
    from datetime import UTC, datetime

    now = datetime(2024, 1, 1, tzinfo=UTC)
    indicators = json.dumps([{"key": "SMA", "params": {"period": 2}}])
    mock_insert.return_value = _row_to_session(
        (
            session_id,
            "BTC/USDT",
            "1d",
            "1d",
            int(sample_candles_df["ts"].iloc[0].timestamp()),
            int(sample_candles_df["ts"].iloc[0].timestamp()) - 86400,
            indicators,
            1.0,
            "paused",
            now,
            now,
        )
    )
    mock_load.return_value = sample_candles_df
    latest = int(sample_candles_df["ts"].iloc[-1].timestamp())
    mock_range.return_value = (int(sample_candles_df["ts"].iloc[0].timestamp()), latest, 5)

    store = ReplaySessionStore()
    conn = MagicMock()
    engine = store.create(
        conn,
        ReplaySessionCreate(
            symbol="BTC/USDT",
            timeframe="1d",
            start=int(sample_candles_df["ts"].iloc[0].timestamp()),
            indicators=[IndicatorSpec(key="SMA", params={"period": 2})],
            step_timeframe="1d",
        ),
    )

    ticks, _ = engine.step_batch(conn, count=2)
    assert len(ticks) == 2
    assert "SMA_2" in ticks[0].indicators
    assert len(ticks[1].indicators["SMA_2"]) == 2


@patch("api.services.replay_session_store.SymbolService.require_active_symbol")
@patch("api.services.replay_session_store.ReplayRepository.insert")
@patch("api.services.replay_engine.CandleService.load_dataframe")
@patch("api.services.replay_engine.CandleService.get_data_range")
def test_replay_seek_out_of_range(
    mock_range: MagicMock,
    mock_load: MagicMock,
    mock_insert: MagicMock,
    _mock_symbol: MagicMock,
    sample_candles_df: pd.DataFrame,
) -> None:
    """Seek before start anchor raises validation error."""
    import json
    from datetime import UTC, datetime

    from api.repositories.replay_repository import _row_to_session

    session_id = uuid4()
    now = datetime(2024, 1, 1, tzinfo=UTC)
    start = int(sample_candles_df["ts"].iloc[0].timestamp())
    indicators = json.dumps([])
    mock_insert.return_value = _row_to_session(
        (session_id, "BTC/USDT", "1d", "1d", start, start - 86400, indicators, 1.0, "paused", now, now)
    )
    mock_load.return_value = sample_candles_df
    latest = int(sample_candles_df["ts"].iloc[-1].timestamp())
    mock_range.return_value = (start, latest, 5)

    store = ReplaySessionStore()
    conn = MagicMock()
    engine = store.create(
        conn,
        ReplaySessionCreate(symbol="BTC/USDT", timeframe="1d", start=start, step_timeframe="1d"),
    )

    import pytest

    from api.exceptions import ValidationError

    with pytest.raises(ValidationError):
        engine.seek(conn, 1)
