"""
Tests for the run_sync CLI entry point.
"""

from argparse import Namespace
from typing import Any

import run_sync
from data.sync import SyncResult


def test_main_requires_exactly_one_mode(monkeypatch) -> None:
    """No mode selected returns usage error code 2."""
    monkeypatch.setattr(run_sync, "parse_args", lambda: Namespace(once=False, backfill=False))
    assert run_sync.main() == 2


def test_main_rejects_both_modes_selected(monkeypatch) -> None:
    """Selecting --once and --backfill together returns usage error code 2."""
    monkeypatch.setattr(run_sync, "parse_args", lambda: Namespace(once=True, backfill=True))
    assert run_sync.main() == 2


def test_main_returns_zero_when_all_symbols_succeed_once(monkeypatch) -> None:
    """A fully successful sync pass exits with code 0."""
    monkeypatch.setattr(run_sync, "parse_args", lambda: Namespace(once=True, backfill=False))
    monkeypatch.setattr(run_sync, "run_migrations_on_startup", lambda: 0)
    monkeypatch.setattr(run_sync, "load_data_config", lambda: object())

    def fake_sync_all(_config: object, progress_callback: Any = None) -> list[SyncResult]:
        if progress_callback is not None:
            progress_callback(1, 1, SyncResult("BTC/USDT", "1m", 10, 10, 0, 0, "ok"))
        return [SyncResult("BTC/USDT", "1m", 10, 10, 0, 0, "ok")]

    monkeypatch.setattr(run_sync, "sync_all", fake_sync_all)
    assert run_sync.main() == 0


def test_main_returns_zero_when_all_symbols_succeed_backfill(monkeypatch) -> None:
    """Backfill mode also exits with code 0 when all symbols succeed."""
    monkeypatch.setattr(run_sync, "parse_args", lambda: Namespace(once=False, backfill=True))
    monkeypatch.setattr(run_sync, "run_migrations_on_startup", lambda: 0)
    monkeypatch.setattr(run_sync, "load_data_config", lambda: object())
    monkeypatch.setattr(
        run_sync,
        "sync_all",
        lambda _config, progress_callback=None: [SyncResult("BTC/USDT", "1m", 10, 10, 0, 0, "ok")],
    )
    assert run_sync.main() == 0


def test_main_returns_one_when_any_symbol_fails(monkeypatch) -> None:
    """Any failed symbol should produce a non-zero process exit code."""
    monkeypatch.setattr(run_sync, "parse_args", lambda: Namespace(once=True, backfill=False))
    monkeypatch.setattr(run_sync, "run_migrations_on_startup", lambda: 0)
    monkeypatch.setattr(run_sync, "load_data_config", lambda: object())
    monkeypatch.setattr(
        run_sync,
        "sync_all",
        lambda _config, progress_callback=None: [
            SyncResult("BTC/USDT", "1m", 10, 10, 0, 0, "ok"),
            SyncResult("ETH/USDT", "1m", 0, 0, 0, 0, "failed", "exchange down"),
        ],
    )
    assert run_sync.main() == 1
