"""
Tests for run_backtest data preconditions in Phase 1.
"""

import pytest

import run_backtest
from exceptions import DataGapError


def test_ensure_data_raises_when_canonical_1m_missing(monkeypatch) -> None:
    """run_backtest should fail clearly when sync has not populated 1m candles."""
    monkeypatch.setattr(run_backtest, "run_migrations_on_startup", lambda: 0)
    monkeypatch.setattr(run_backtest, "candle_count", lambda symbol, timeframe: 0)

    with pytest.raises(DataGapError, match="run_sync.py --backfill"):
        run_backtest.ensure_data("BTC/USDT")


def test_ensure_data_passes_when_canonical_1m_exists(monkeypatch) -> None:
    """When canonical rows exist, ensure_data should not fetch and should succeed."""
    monkeypatch.setattr(run_backtest, "run_migrations_on_startup", lambda: 0)
    monkeypatch.setattr(run_backtest, "candle_count", lambda symbol, timeframe: 1000)
    run_backtest.ensure_data("BTC/USDT")
