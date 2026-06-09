"""
Load the data ingestion configuration from data.yaml.

This is sync-only config (exchanges, symbol universe, history depth, scheduling).
Backtest/runtime settings stay in config.yaml and are loaded by the top-level config
module. Keeping the two separate stops sync changes from leaking into backtest runs.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

# data.yaml lives at the project root, alongside config.yaml (one level up from data/).
DEFAULT_DATA_CONFIG_PATH = Path(__file__).parent.parent / "data.yaml"


@dataclass(frozen=True)
class ExchangeConfig:
    """Primary exchange plus ordered fallbacks used when the primary fetch fails."""

    primary: str
    fallback: tuple[str, ...]

    @property
    def ordered(self) -> tuple[str, ...]:
        """Return all exchanges to try, primary first then fallbacks in order."""
        return (self.primary, *self.fallback)


@dataclass(frozen=True)
class SymbolConfig:
    """A single trading pair and its initial backfill history depth (e.g. '8y')."""

    symbol: str
    history: str


@dataclass(frozen=True)
class SyncConfig:
    """Scheduling and write-policy settings for the sync orchestrator."""

    mode: str
    interval_minutes: int
    max_concurrent_symbols: int
    store_in_progress_candle: bool
    overwrite_closed_candles: bool
    retry_gaps: bool


@dataclass(frozen=True)
class DataConfig:
    """Top-level ingestion config parsed from data.yaml."""

    timeframe: str
    exchanges: ExchangeConfig
    quote_currency: str
    symbols: tuple[SymbolConfig, ...]
    sync: SyncConfig


def _parse_exchanges(raw: dict[str, Any]) -> ExchangeConfig:
    """
    Build the ExchangeConfig from the raw 'exchanges' mapping.

    Args:
        raw: The 'exchanges' section of data.yaml.

    Returns:
        Parsed ExchangeConfig with primary and ordered fallbacks.

    Raises:
        ValueError: If 'primary' is missing.
    """
    primary = raw.get("primary")
    if not primary:
        raise ValueError("data.yaml exchanges section must define 'primary'")
    fallback = tuple(str(name) for name in raw.get("fallback", []))
    return ExchangeConfig(primary=str(primary), fallback=fallback)


def _parse_symbols(raw: dict[str, Any], quote_currency: str) -> tuple[SymbolConfig, ...]:
    """
    Build the symbol universe from the raw 'symbols' mapping.

    Args:
        raw: The 'symbols' section mapping pair -> {history: ...}.
        quote_currency: Expected quote currency every symbol must trade against.

    Returns:
        Tuple of SymbolConfig in declaration order.

    Raises:
        ValueError: If empty, if a symbol's quote currency is wrong, or history is missing.
    """
    if not raw:
        raise ValueError("data.yaml must define at least one symbol")

    symbols: list[SymbolConfig] = []
    for symbol, settings in raw.items():
        if not symbol.endswith(f"/{quote_currency}"):
            raise ValueError(
                f"Symbol {symbol} must use quote currency {quote_currency} "
                f"(e.g. BTC/{quote_currency})"
            )
        history = (settings or {}).get("history")
        if not history:
            raise ValueError(f"Symbol {symbol} must define a 'history' depth, e.g. 4y")
        symbols.append(SymbolConfig(symbol=str(symbol), history=str(history)))
    return tuple(symbols)


def _parse_sync(raw: dict[str, Any]) -> SyncConfig:
    """
    Build the SyncConfig from the raw 'sync' mapping, applying safe defaults.

    Args:
        raw: The 'sync' section of data.yaml.

    Returns:
        Parsed SyncConfig.
    """
    return SyncConfig(
        mode=str(raw.get("mode", "cron")),
        interval_minutes=int(raw.get("interval_minutes", 60)),
        max_concurrent_symbols=int(raw.get("max_concurrent_symbols", 3)),
        # Default to never storing the in-progress candle or rewriting closed bars (OQ-04).
        store_in_progress_candle=bool(raw.get("store_in_progress_candle", False)),
        overwrite_closed_candles=bool(raw.get("overwrite_closed_candles", False)),
        retry_gaps=bool(raw.get("retry_gaps", True)),
    )


def load_data_config(path: Path | None = None) -> DataConfig:
    """
    Load and validate the data ingestion configuration from data.yaml.

    Args:
        path: Path to data.yaml. Defaults to the project root data.yaml.

    Returns:
        Parsed DataConfig instance.

    Raises:
        FileNotFoundError: If the config file does not exist.
        ValueError: If required keys are missing or invalid.
    """
    config_path = path or DEFAULT_DATA_CONFIG_PATH
    if not config_path.exists():
        raise FileNotFoundError(f"Data config file not found: {config_path}")

    with config_path.open(encoding="utf-8") as handle:
        raw: dict[str, Any] = yaml.safe_load(handle)

    if not raw:
        raise ValueError(f"Data config file is empty: {config_path}")

    timeframe = raw.get("timeframe")
    if not timeframe:
        raise ValueError("data.yaml must define 'timeframe' (canonical store resolution)")

    quote_currency = str(raw.get("quote_currency", "USDT"))

    return DataConfig(
        timeframe=str(timeframe),
        exchanges=_parse_exchanges(raw.get("exchanges", {})),
        quote_currency=quote_currency,
        symbols=_parse_symbols(raw.get("symbols", {}), quote_currency),
        sync=_parse_sync(raw.get("sync", {})),
    )
