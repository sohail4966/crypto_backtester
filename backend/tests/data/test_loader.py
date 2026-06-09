"""
Tests for get_candles() routing between direct and derived repository reads.
"""

import pandas as pd

from data import loader


def test_get_candles_uses_direct_read_for_1m(monkeypatch) -> None:
    """1m candles are read directly from stored rows."""

    class _Repo:
        def find_by_date_range(self, symbol, timeframe, start, end):
            return [("2024-01-01T00:00:00+00:00", 1.0, 2.0, 0.5, 1.5, 10.0)], [
                "ts",
                "open",
                "high",
                "low",
                "close",
                "volume",
            ]

        def find_derived_by_date_range(self, symbol, timeframe, start, end):
            raise AssertionError("derived path should not be used for 1m")

    monkeypatch.setattr(loader, "_repository", _Repo())
    candles = loader.get_candles("BTC/USDT", "1m", "2024-01-01", "2024-01-02")
    assert len(candles) == 1
    assert str(candles["ts"].dt.tz) == "UTC"


def test_get_candles_uses_derived_read_for_higher_timeframes(monkeypatch) -> None:
    """Non-1m requests are derived from canonical stored 1m rows."""

    class _Repo:
        def find_by_date_range(self, symbol, timeframe, start, end):
            raise AssertionError("direct path should not be used for derived timeframe")

        def find_derived_by_date_range(self, symbol, timeframe, start, end):
            assert timeframe == "1d"
            return [("2024-01-01T00:00:00+00:00", 1.0, 2.0, 0.5, 1.5, 10.0)], [
                "ts",
                "open",
                "high",
                "low",
                "close",
                "volume",
            ]

    monkeypatch.setattr(loader, "_repository", _Repo())
    candles = loader.get_candles("BTC/USDT", "1d", "2024-01-01", "2024-01-31")
    assert len(candles) == 1
    assert candles["ts"].iloc[0] == pd.Timestamp("2024-01-01T00:00:00Z")
