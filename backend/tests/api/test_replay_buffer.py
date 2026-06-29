"""Tests for replay buffer load, trim, extend, and tick slicing."""

from __future__ import annotations

import pandas as pd

from api.schemas.indicators import IndicatorSpec
from api.services.overlay_pipeline import OverlayPipeline
from api.services.replay_buffer import ReplayBuffer


def _sample_frame(n: int = 10) -> pd.DataFrame:
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


def test_buffer_load_and_slice_ticks() -> None:
    """Initial load reveals bars one at a time from precomputed overlays."""
    frame = _sample_frame(8)
    buffer = ReplayBuffer()
    start_anchor = int(frame["ts"].iloc[2].timestamp())
    cursor_ts = int(frame["ts"].iloc[1].timestamp())
    latest = int(frame["ts"].iloc[-1].timestamp())
    pipeline = OverlayPipeline()

    buffer.load(
        frame,
        [IndicatorSpec(key="SMA", params={"period": 2})],
        start_anchor=start_anchor,
        cursor_ts=cursor_ts,
        pipeline=pipeline,
        latest_available_ts=latest,
    )

    assert buffer.cursor_idx == 1
    ticks = buffer.slice_ticks(2)
    assert len(ticks) == 2
    assert ticks[0].bar.time == int(frame["ts"].iloc[2].timestamp())
    assert "SMA_2" in ticks[0].indicators


def test_buffer_trim_drops_old_bars() -> None:
    """Trim keeps at most max_trail bars behind cursor."""
    frame = _sample_frame(20)
    buffer = ReplayBuffer()
    start_anchor = int(frame["ts"].iloc[0].timestamp())
    cursor_ts = start_anchor - 86400
    latest = int(frame["ts"].iloc[-1].timestamp())

    buffer.load(
        frame,
        [],
        start_anchor=start_anchor,
        cursor_ts=cursor_ts,
        pipeline=OverlayPipeline(),
        latest_available_ts=latest,
    )
    buffer.slice_ticks(15)
    assert buffer.cursor_idx == 14
    buffer.trim_trail(5, warmup_bars=0)
    assert buffer.cursor_idx == 4
    assert len(buffer.frame) == 10


def test_buffer_trim_respects_warmup_floor() -> None:
    """Trim keeps enough history for indicator warmup recompute on extend."""
    frame = _sample_frame(30)
    buffer = ReplayBuffer()
    start_anchor = int(frame["ts"].iloc[0].timestamp())
    cursor_ts = start_anchor - 86400
    latest = int(frame["ts"].iloc[-1].timestamp())

    buffer.load(
        frame,
        [IndicatorSpec(key="SMA", params={"period": 10})],
        start_anchor=start_anchor,
        cursor_ts=cursor_ts,
        pipeline=OverlayPipeline(),
        latest_available_ts=latest,
    )
    buffer.slice_ticks(20)
    assert buffer.cursor_idx == 19

    buffer.trim_trail(15, warmup_bars=0)
    assert buffer.cursor_idx == 14

    buffer2 = ReplayBuffer()
    buffer2.load(
        frame,
        [IndicatorSpec(key="SMA", params={"period": 10})],
        start_anchor=start_anchor,
        cursor_ts=cursor_ts,
        pipeline=OverlayPipeline(),
        latest_available_ts=latest,
    )
    buffer2.slice_ticks(20)
    buffer2.trim_trail(15, warmup_bars=10)
    assert buffer2.cursor_idx == 9


def test_buffer_append_extends_prefetch() -> None:
    """Appending rows extends prefetch_end_idx and overlays."""
    frame = _sample_frame(5)
    buffer = ReplayBuffer()
    start_anchor = int(frame["ts"].iloc[0].timestamp())
    latest = int(frame["ts"].iloc[-1].timestamp()) + 86400 * 5
    pipeline = OverlayPipeline()

    buffer.load(
        frame,
        [IndicatorSpec(key="SMA", params={"period": 2})],
        start_anchor=start_anchor,
        cursor_ts=start_anchor - 86400,
        pipeline=pipeline,
        latest_available_ts=latest,
    )
    before = buffer.prefetch_end_idx
    extra = _sample_frame(3)
    extra["ts"] = pd.date_range("2024-01-06", periods=3, freq="D", tz="UTC")
    buffer.append_frame(extra, [IndicatorSpec(key="SMA", params={"period": 2})], pipeline)
    assert buffer.prefetch_end_idx > before
