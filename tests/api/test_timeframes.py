"""Tests for timeframe configuration."""

from __future__ import annotations

from api.services.timeframes import SUPPORTED_TIMEFRAMES, TIMEFRAME_SECONDS


def test_supported_timeframes_include_new_intervals() -> None:
    """Derived intervals are exposed through the API."""
    for timeframe in ("3m", "30m", "2h", "1w", "1M"):
        assert timeframe in SUPPORTED_TIMEFRAMES


def test_timeframe_seconds_cover_all_supported() -> None:
    """Every supported timeframe has a bar duration for warmup shifting."""
    assert set(TIMEFRAME_SECONDS) == set(SUPPORTED_TIMEFRAMES)
