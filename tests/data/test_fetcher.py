"""
Tests for incremental fetch, closed-candle filtering, and exchange fallback.
"""

import ccxt
import pandas as pd
import pytest

from data import fetcher

MINUTE_MS = 60_000
# Minute-aligned base timestamp so candle boundaries are exact.
BASE_MS = 1_700_000_000_000 - (1_700_000_000_000 % MINUTE_MS)


def _candle_row(ts_ms: int) -> list[float | int]:
    """Build a single OHLCV row at the given epoch-ms timestamp."""
    return [ts_ms, 1.0, 2.0, 0.5, 1.5, 10.0]


class _FakeExchange:
    """Minimal ccxt-like exchange serving preloaded rows from a since cursor."""

    def __init__(self, rows: list[list[float | int]]) -> None:
        self.rows = rows
        self.since_calls: list[int] = []

    def fetch_ohlcv(
        self, symbol: str, timeframe: str, since: int, limit: int
    ) -> list[list[float | int]]:
        """Return up to limit rows at or after since."""
        self.since_calls.append(since)
        available = [row for row in self.rows if row[0] >= since]
        return available[:limit]


class _RaisingExchange:
    """Exchange whose fetch always fails, to exercise fallback."""

    def fetch_ohlcv(
        self, symbol: str, timeframe: str, since: int, limit: int
    ) -> list[list[float | int]]:
        """Always raise a ccxt network error."""
        raise ccxt.NetworkError("exchange unavailable")


def test_timeframe_to_ms_known_and_unknown() -> None:
    """Known timeframes resolve; unknown ones raise."""
    assert fetcher.timeframe_to_ms("1m") == MINUTE_MS
    with pytest.raises(ValueError, match="Unsupported timeframe"):
        fetcher.timeframe_to_ms("7s")


def test_fetch_since_drops_in_progress_candle(monkeypatch: pytest.MonkeyPatch) -> None:
    """The current still-forming candle is excluded from returned rows."""
    rows = [_candle_row(BASE_MS + i * MINUTE_MS) for i in range(3)]
    monkeypatch.setattr(fetcher, "_build_exchange", lambda _id: _FakeExchange(rows))
    # now falls inside the third candle, so only the first two are closed.
    now_ms = BASE_MS + 2 * MINUTE_MS + 30_000

    candles = fetcher.fetch_since("BTC/USDT", BASE_MS, "binance", "1m", now_ms=now_ms)

    assert len(candles) == 2
    assert candles["ts"].iloc[-1] == pd.to_datetime(BASE_MS + MINUTE_MS, unit="ms", utc=True)


def test_fetch_since_paginates_and_dedupes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pagination walks past the batch limit and drops boundary duplicates."""
    rows = [_candle_row(BASE_MS + i * MINUTE_MS) for i in range(5)]
    fake = _FakeExchange(rows)
    monkeypatch.setattr(fetcher, "_build_exchange", lambda _id: fake)
    monkeypatch.setattr(fetcher, "CCXT_BATCH_LIMIT", 2)
    # All five candles are closed relative to now.
    now_ms = BASE_MS + 10 * MINUTE_MS

    candles = fetcher.fetch_since("BTC/USDT", BASE_MS, "binance", "1m", now_ms=now_ms)

    assert len(candles) == 5
    assert candles["ts"].is_monotonic_increasing
    assert len(fake.since_calls) > 1


def test_fetch_since_respects_until_bound(monkeypatch: pytest.MonkeyPatch) -> None:
    """An until_ms bound trims returned candles to the requested range."""
    rows = [_candle_row(BASE_MS + i * MINUTE_MS) for i in range(5)]
    monkeypatch.setattr(fetcher, "_build_exchange", lambda _id: _FakeExchange(rows))
    now_ms = BASE_MS + 100 * MINUTE_MS
    until_ms = BASE_MS + 2 * MINUTE_MS

    candles = fetcher.fetch_since(
        "BTC/USDT", BASE_MS, "binance", "1m", now_ms=now_ms, until_ms=until_ms
    )

    assert len(candles) == 3
    assert candles["ts"].iloc[-1] == pd.to_datetime(until_ms, unit="ms", utc=True)


def test_fetch_since_rejects_negative_since() -> None:
    """A negative since_ms is rejected."""
    with pytest.raises(ValueError, match="since_ms"):
        fetcher.fetch_since("BTC/USDT", -1, "binance", "1m")


def test_fetch_since_with_fallback_uses_next_exchange(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the primary fails, the next exchange in order is used."""
    rows = [_candle_row(BASE_MS)]

    def build(exchange_id: str) -> object:
        if exchange_id in ("binance", "bybit"):
            return _RaisingExchange()
        return _FakeExchange(rows)

    monkeypatch.setattr(fetcher, "_build_exchange", build)
    now_ms = BASE_MS + 10 * MINUTE_MS

    candles = fetcher.fetch_since_with_fallback(
        "BTC/USDT", BASE_MS, ("binance", "bybit", "okx"), "1m", now_ms=now_ms
    )

    assert len(candles) == 1


def test_fetch_since_with_fallback_raises_when_all_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If every exchange fails, the last error propagates."""
    monkeypatch.setattr(fetcher, "_build_exchange", lambda _id: _RaisingExchange())

    with pytest.raises(ccxt.BaseError):
        fetcher.fetch_since_with_fallback("BTC/USDT", BASE_MS, ("binance", "bybit", "okx"), "1m")


def test_fetch_since_with_fallback_requires_exchanges() -> None:
    """An empty exchange list is a programming error."""
    with pytest.raises(ValueError, match="at least one exchange"):
        fetcher.fetch_since_with_fallback("BTC/USDT", BASE_MS, (), "1m")
