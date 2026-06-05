"""
Tests for the sync orchestrator: incremental decision, gap retry, isolation, concurrency.
"""

import threading
import time
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import ccxt
import pandas as pd
import pytest

from data import sync
from data.config import SyncConfig, load_data_config
from data.gaps import GapAuditSummary
from data.repository import Gap

LATEST = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)


def _sync_config(retry_gaps: bool = False, max_concurrent: int = 3) -> SyncConfig:
    """Build a SyncConfig for tests."""
    return SyncConfig(
        mode="cron",
        interval_minutes=60,
        max_concurrent_symbols=max_concurrent,
        store_in_progress_candle=False,
        overwrite_closed_candles=False,
        retry_gaps=retry_gaps,
    )


def _candles(count: int) -> pd.DataFrame:
    """Build a small closed-candle DataFrame with count rows."""
    base_ms = int(LATEST.timestamp() * 1000)
    ts = pd.to_datetime([base_ms + i * sync.MINUTE_MS for i in range(count)], unit="ms", utc=True)
    return pd.DataFrame(
        {
            "ts": ts,
            "open": [1.0] * count,
            "high": [2.0] * count,
            "low": [0.5] * count,
            "close": [1.5] * count,
            "volume": [10.0] * count,
        }
    )


def test_history_to_timedelta_units() -> None:
    """History strings map to the expected durations; bad input raises."""
    assert sync.history_to_timedelta("8y") == timedelta(days=365 * 8)
    assert sync.history_to_timedelta("30d") == timedelta(days=30)
    assert sync.history_to_timedelta("2w") == timedelta(weeks=2)
    assert sync.history_to_timedelta("12h") == timedelta(hours=12)
    with pytest.raises(ValueError, match="Unsupported history"):
        sync.history_to_timedelta("3months")


def test_since_ms_full_history_when_empty() -> None:
    """With no stored data, fetch starts a full history depth back from now."""
    now_ms = int(LATEST.timestamp() * 1000)
    since_ms = sync._since_ms_for_symbol(None, "1y", now_ms)
    assert since_ms == now_ms - int(timedelta(days=365).total_seconds() * 1000)


def test_since_ms_incremental_overlaps_one_minute() -> None:
    """With stored data, fetch resumes one minute before the latest candle."""
    now_ms = int(LATEST.timestamp() * 1000)
    since_ms = sync._since_ms_for_symbol(LATEST, "1y", now_ms)
    assert since_ms == int(LATEST.timestamp() * 1000) - sync.MINUTE_MS


def test_sync_symbol_incremental_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """A successful pass reports fetched/inserted counts and detected gaps."""
    candle_repo = MagicMock()
    candle_repo.latest_timestamp.return_value = LATEST
    candle_repo.insert_new_candles.return_value = 3
    gap_repo = MagicMock()
    monkeypatch.setattr(sync, "fetch_since_with_fallback", lambda *a, **k: _candles(3))
    monkeypatch.setattr(
        sync, "reconcile_gaps", lambda *a, **k: GapAuditSummary("BTC/USDT", "1m", 1, 0, ())
    )

    result = sync.sync_symbol(
        "BTC/USDT",
        "8y",
        ("binance",),
        _sync_config(retry_gaps=False),
        "1m",
        candle_repo,
        gap_repo,
        now_ms=int(LATEST.timestamp() * 1000) + 10 * sync.MINUTE_MS,
    )

    assert result.status == "ok"
    assert result.fetched == 3
    assert result.inserted == 3
    assert result.gaps_created == 1
    assert result.gaps_resolved == 0


def test_sync_symbol_isolates_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """An exchange failure is captured as a failed result, not raised."""
    candle_repo = MagicMock()
    candle_repo.latest_timestamp.return_value = LATEST

    def boom(*args: object, **kwargs: object) -> pd.DataFrame:
        raise ccxt.NetworkError("exchange down")

    monkeypatch.setattr(sync, "fetch_since_with_fallback", boom)

    result = sync.sync_symbol(
        "BTC/USDT", "8y", ("binance",), _sync_config(), "1m", candle_repo, MagicMock()
    )

    assert result.status == "failed"
    assert "exchange down" in result.error


def test_sync_symbol_retries_open_gaps_with_bounded_fetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Open gaps are re-fetched within their bounds and retry is recorded."""
    candle_repo = MagicMock()
    candle_repo.latest_timestamp.return_value = LATEST
    candle_repo.insert_new_candles.return_value = 1
    gap = Gap(5, "BTC/USDT", "1m", LATEST, LATEST + timedelta(minutes=1), "open", 0)
    gap_repo = MagicMock()
    gap_repo.find_open_gaps.return_value = [gap]

    calls: list[dict[str, object]] = []

    def record_fetch(*args: object, **kwargs: object) -> pd.DataFrame:
        calls.append(kwargs)
        return _candles(1)

    monkeypatch.setattr(sync, "fetch_since_with_fallback", record_fetch)
    monkeypatch.setattr(
        sync, "reconcile_gaps", lambda *a, **k: GapAuditSummary("BTC/USDT", "1m", 0, 1, ())
    )

    result = sync.sync_symbol(
        "BTC/USDT",
        "8y",
        ("binance",),
        _sync_config(retry_gaps=True),
        "1m",
        candle_repo,
        gap_repo,
        now_ms=int(LATEST.timestamp() * 1000) + 10 * sync.MINUTE_MS,
    )

    assert result.status == "ok"
    gap_repo.record_gap_retry.assert_called_once_with(5)
    # The gap re-fetch is bounded by the gap's end timestamp.
    bounded_calls = [c for c in calls if c.get("until_ms") is not None]
    assert bounded_calls, "expected a bounded gap re-fetch"


def test_sync_all_runs_every_symbol(monkeypatch: pytest.MonkeyPatch) -> None:
    """sync_all returns one result per configured symbol."""
    config = load_data_config()

    def fake_sync_symbol(
        symbol: str,
        history: str,
        exchanges: tuple[str, ...],
        sync_config: SyncConfig,
        timeframe: str,
        candle_repo: object,
        gap_repo: object,
    ) -> sync.SyncResult:
        return sync.SyncResult(symbol, timeframe, 1, 1, 0, 0, "ok")

    monkeypatch.setattr(sync, "sync_symbol", fake_sync_symbol)

    results = sync.sync_all(config)

    assert {r.symbol for r in results} == {s.symbol for s in config.symbols}


def test_sync_all_limits_concurrency(monkeypatch: pytest.MonkeyPatch) -> None:
    """No more than max_concurrent_symbols workers run at once."""
    config = load_data_config()
    lock = threading.Lock()
    state = {"current": 0, "max": 0}

    def fake_sync_symbol(
        symbol: str,
        history: str,
        exchanges: tuple[str, ...],
        sync_config: SyncConfig,
        timeframe: str,
        candle_repo: object,
        gap_repo: object,
    ) -> sync.SyncResult:
        with lock:
            state["current"] += 1
            state["max"] = max(state["max"], state["current"])
        time.sleep(0.02)
        with lock:
            state["current"] -= 1
        return sync.SyncResult(symbol, timeframe, 0, 0, 0, 0, "ok")

    monkeypatch.setattr(sync, "sync_symbol", fake_sync_symbol)

    sync.sync_all(config)

    assert state["max"] <= config.sync.max_concurrent_symbols
