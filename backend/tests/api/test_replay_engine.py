"""Tests for replay engine step, seek, and open-ended completion."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pandas as pd
import pytest

from api.exceptions import ValidationError
from api.repositories.replay_repository import ReplaySessionRow
from api.schemas.indicators import IndicatorSpec
from api.services.overlay_pipeline import OverlayPipeline
from api.services.replay_engine import ReplayEngine
from api.services.timeframes import advance_unix_by_bars


def _sample_frame(n: int = 20) -> pd.DataFrame:
    ts = pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC")
    close = pd.Series(range(100, 100 + n), dtype=float)
    return pd.DataFrame(
        {
            "ts": ts,
            "open": close - 1,
            "high": close + 2,
            "low": close - 2,
            "close": close,
            "volume": [1000.0] * n,
        }
    )


def _engine_row() -> ReplaySessionRow:
    from datetime import UTC, datetime

    return ReplaySessionRow(
        session_id=uuid4(),
        symbol="BTC/USDT",
        timeframe="1d",
        step_timeframe="1d",
        start_anchor=int(pd.Timestamp("2024-01-03", tz="UTC").timestamp()),
        cursor_ts=int(pd.Timestamp("2024-01-02", tz="UTC").timestamp()),
        indicators=[IndicatorSpec(key="SMA", params={"period": 2})],
        speed=1.0,
        state="paused",
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
    )


@patch("api.services.replay_engine.CandleService.get_data_range")
@patch("api.services.replay_engine.CandleService.load_dataframe")
def test_engine_step_does_not_recompute_overlays(mock_load: MagicMock, mock_range: MagicMock) -> None:
    """Stepping uses precomputed overlays; pipeline.compute is not called per tick."""
    frame = _sample_frame(30)
    mock_load.return_value = frame
    latest = int(frame["ts"].iloc[-1].timestamp())
    mock_range.return_value = (int(frame["ts"].iloc[0].timestamp()), latest, len(frame))

    real_pipeline = OverlayPipeline()
    mock_pipeline = MagicMock(spec=OverlayPipeline)
    mock_pipeline.warmup_bars.side_effect = real_pipeline.warmup_bars
    mock_pipeline.compute.side_effect = real_pipeline.compute
    mock_pipeline.compute_append.side_effect = real_pipeline.compute_append

    engine = ReplayEngine.from_row(_engine_row(), pipeline=mock_pipeline)
    conn = MagicMock()
    engine.load_buffer(conn)
    assert mock_pipeline.compute.call_count == 1

    mock_pipeline.reset_mock()
    ticks, _ = engine.step_batch(conn, count=10)
    assert len(ticks) == 10
    mock_pipeline.compute.assert_not_called()
    mock_pipeline.compute_append.assert_not_called()


@patch("api.services.replay_engine.settings.replay_prefetch_bars", return_value=1000)
@patch("api.services.replay_engine.CandleService.get_data_range")
@patch("api.services.replay_engine.CandleService.load_dataframe")
def test_engine_load_buffer_fetches_forward(
    mock_load: MagicMock,
    mock_range: MagicMock,
    _mock_prefetch: MagicMock,
) -> None:
    """Initial load requests candles forward from start anchor, not backward."""
    frame = _sample_frame(20)
    mock_load.return_value = frame
    row = _engine_row()
    latest = int(frame["ts"].iloc[-1].timestamp())
    mock_range.return_value = (int(frame["ts"].iloc[0].timestamp()), latest, len(frame))

    engine = ReplayEngine.from_row(row)
    engine.load_buffer(MagicMock())

    args = mock_load.call_args[0]
    load_from = args[3]
    load_to = args[4]
    assert load_from == row.start_anchor
    expected_to = advance_unix_by_bars(row.start_anchor, row.step_timeframe, 1000)
    assert load_to == min(expected_to, latest)
    assert load_to > row.start_anchor


@patch("api.services.replay_engine.CandleService.get_data_range")
@patch("api.services.replay_engine.CandleService.load_dataframe")
def test_engine_seek_within_trail_skips_reload(mock_load: MagicMock, mock_range: MagicMock) -> None:
    """Forward seek inside trail window adjusts cursor without reloading candles."""
    frame = _sample_frame(30)
    mock_load.return_value = frame
    latest = int(frame["ts"].iloc[-1].timestamp())
    mock_range.return_value = (int(frame["ts"].iloc[0].timestamp()), latest, len(frame))

    engine = ReplayEngine.from_row(_engine_row())
    conn = MagicMock()
    engine.load_buffer(conn)
    engine.step_batch(conn, count=5)

    target_ts = int(frame["ts"].iloc[engine.buffer.cursor_idx + 2].timestamp())
    mock_load.reset_mock()
    reloaded = engine.seek(conn, target_ts)

    assert reloaded is False
    mock_load.assert_not_called()
    assert engine.buffer.cursor_ts == target_ts


@patch("api.services.replay_engine.settings.replay_trail_bars", return_value=2)
@patch("api.services.replay_engine.CandleService.get_data_range")
@patch("api.services.replay_engine.CandleService.load_dataframe")
def test_engine_seek_beyond_trail_reloads_buffer(
    mock_load: MagicMock,
    mock_range: MagicMock,
    _mock_trail: MagicMock,
) -> None:
    """Seek outside trail window reloads candles and returns buffer_reset signal."""
    frame = _sample_frame(30)
    mock_load.return_value = frame
    latest = int(frame["ts"].iloc[-1].timestamp())
    mock_range.return_value = (int(frame["ts"].iloc[0].timestamp()), latest, len(frame))

    engine = ReplayEngine.from_row(_engine_row())
    conn = MagicMock()
    engine.load_buffer(conn)
    engine.step_batch(conn, count=8)

    back_ts = int(frame["ts"].iloc[2].timestamp())
    assert back_ts >= engine.start_anchor
    mock_load.reset_mock()
    reloaded = engine.seek(conn, back_ts)

    assert reloaded is True
    mock_load.assert_called_once()


@patch("api.services.replay_engine.CandleService.get_data_range")
@patch("api.services.replay_engine.CandleService.load_dataframe")
def test_engine_seek_before_start_raises(mock_load: MagicMock, mock_range: MagicMock) -> None:
    """Seek before start anchor is rejected."""
    frame = _sample_frame(10)
    mock_load.return_value = frame
    latest = int(frame["ts"].iloc[-1].timestamp())
    mock_range.return_value = (int(frame["ts"].iloc[0].timestamp()), latest, len(frame))

    engine = ReplayEngine.from_row(_engine_row())
    conn = MagicMock()
    engine.load_buffer(conn)

    with pytest.raises(ValidationError):
        engine.seek(conn, engine.start_anchor - 99999)


@patch("api.services.replay_engine.CandleService.get_data_range")
@patch("api.services.replay_engine.CandleService.load_dataframe")
def test_engine_completes_at_latest(mock_load: MagicMock, mock_range: MagicMock) -> None:
    """Open-ended replay completes when latest candle is reached."""
    frame = _sample_frame(5)
    mock_load.return_value = frame
    latest = int(frame["ts"].iloc[-1].timestamp())
    mock_range.return_value = (int(frame["ts"].iloc[0].timestamp()), latest, len(frame))

    engine = ReplayEngine.from_row(_engine_row())
    conn = MagicMock()
    engine.load_buffer(conn)

    while engine.buffer.can_step():
        engine.step_batch(conn, count=1)

    assert engine.state == "completed"


@patch("api.services.replay_engine.CandleService.get_data_range")
@patch("api.services.replay_engine.CandleService.load_dataframe")
def test_engine_step_latency_does_not_grow_linearly(mock_load: MagicMock, mock_range: MagicMock) -> None:
    """Wall time for a fixed batch size stays bounded as cursor advances through the buffer."""
    import time

    frame = _sample_frame(300)
    mock_load.return_value = frame
    latest = int(frame["ts"].iloc[-1].timestamp())
    mock_range.return_value = (int(frame["ts"].iloc[0].timestamp()), latest, len(frame))

    engine = ReplayEngine.from_row(_engine_row())
    conn = MagicMock()
    engine.load_buffer(conn)

    def step_batch_seconds(count: int) -> float:
        start = time.perf_counter()
        engine.step_batch(conn, count=count)
        return time.perf_counter() - start

    early = step_batch_seconds(50)
    engine.step_batch(conn, count=150)
    late = step_batch_seconds(50)

    # O(1) per tick: late batch should not scale linearly with cursor depth.
    assert late < early * 5 + 0.05
