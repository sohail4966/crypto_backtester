"""
Tests for data.yaml ingestion config loading and validation.
"""

from pathlib import Path

import pytest

from data.config import load_data_config

APPROVED_SYMBOLS = {
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
}


def test_load_data_config_contains_approved_symbol_universe() -> None:
    """data.yaml defines exactly the 3 approved Phase 1 USDT spot symbols."""
    config = load_data_config()
    symbols = {symbol.symbol for symbol in config.symbols}
    assert symbols == APPROVED_SYMBOLS


def test_load_data_config_stores_canonical_1m_timeframe() -> None:
    """Phase 1 stores only canonical 1m candles."""
    config = load_data_config()
    assert config.timeframe == "1m"


def test_load_data_config_exchange_fallback_order() -> None:
    """Primary is binance with bybit then okx fallbacks, primary first in ordered()."""
    config = load_data_config()
    assert config.exchanges.primary == "binance"
    assert config.exchanges.fallback == ("bybit", "okx")
    assert config.exchanges.ordered == ("binance", "bybit", "okx")


def test_load_data_config_sync_policy_defaults() -> None:
    """Sync defaults to not storing in-progress candles or overwriting closed bars."""
    config = load_data_config()
    assert config.sync.max_concurrent_symbols == 3
    assert config.sync.store_in_progress_candle is False
    assert config.sync.overwrite_closed_candles is False
    assert config.sync.retry_gaps is True


def test_load_data_config_per_symbol_history_depth() -> None:
    """BTC keeps the longest history; alts use a shorter window."""
    config = load_data_config()
    history_by_symbol = {symbol.symbol: symbol.history for symbol in config.symbols}
    assert history_by_symbol["BTC/USDT"] == "8y"
    assert history_by_symbol["SOL/USDT"] == "4y"


def test_load_data_config_missing_file_raises(tmp_path: Path) -> None:
    """A missing data.yaml raises FileNotFoundError, not a silent default."""
    with pytest.raises(FileNotFoundError):
        load_data_config(tmp_path / "does_not_exist.yaml")


def test_load_data_config_rejects_wrong_quote_currency(tmp_path: Path) -> None:
    """A non-USDT pair is rejected to keep the universe consistent."""
    config_path = tmp_path / "data.yaml"
    config_path.write_text(
        "timeframe: 1m\n"
        "quote_currency: USDT\n"
        "exchanges:\n"
        "  primary: binance\n"
        "symbols:\n"
        "  BTC/USD:\n"
        "    history: 4y\n"
        "sync: {}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="quote currency"):
        load_data_config(config_path)


def test_load_data_config_rejects_symbol_without_history(tmp_path: Path) -> None:
    """A symbol missing its history depth is rejected."""
    config_path = tmp_path / "data.yaml"
    config_path.write_text(
        "timeframe: 1m\n"
        "quote_currency: USDT\n"
        "exchanges:\n"
        "  primary: binance\n"
        "symbols:\n"
        "  BTC/USDT: {}\n"
        "sync: {}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="history"):
        load_data_config(config_path)
