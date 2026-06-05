"""
Tests for the run_sync CLI entry point.
"""

from argparse import Namespace

import run_sync
from data.sync import SyncResult


def test_main_requires_once_flag(monkeypatch) -> None:
    """Without --once, run_sync returns usage error code 2."""
    monkeypatch.setattr(run_sync, "parse_args", lambda: Namespace(once=False))
    assert run_sync.main() == 2


def test_main_returns_zero_when_all_symbols_succeed(monkeypatch) -> None:
    """A fully successful sync pass exits with code 0."""
    monkeypatch.setattr(run_sync, "parse_args", lambda: Namespace(once=True))
    monkeypatch.setattr(run_sync, "run_migrations_on_startup", lambda: 0)
    monkeypatch.setattr(run_sync, "load_data_config", lambda: object())
    monkeypatch.setattr(
        run_sync,
        "sync_all",
        lambda _config: [SyncResult("BTC/USDT", "1m", 10, 10, 0, 0, "ok")],
    )
    assert run_sync.main() == 0


def test_main_returns_one_when_any_symbol_fails(monkeypatch) -> None:
    """Any failed symbol should produce a non-zero process exit code."""
    monkeypatch.setattr(run_sync, "parse_args", lambda: Namespace(once=True))
    monkeypatch.setattr(run_sync, "run_migrations_on_startup", lambda: 0)
    monkeypatch.setattr(run_sync, "load_data_config", lambda: object())
    monkeypatch.setattr(
        run_sync,
        "sync_all",
        lambda _config: [
            SyncResult("BTC/USDT", "1m", 10, 10, 0, 0, "ok"),
            SyncResult("ETH/USDT", "1m", 0, 0, 0, 0, "failed", "exchange down"),
        ],
    )
    assert run_sync.main() == 1
