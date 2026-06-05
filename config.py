"""
Load application configuration from config.yaml and environment variables.

Secrets (DATABASE_URL) come from .env via python-dotenv, never from config.yaml.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from signals.types import Strategy

DEFAULT_CONFIG_PATH = Path(__file__).parent / "config.yaml"


@dataclass(frozen=True)
class AppConfig:
    """Runtime settings for the POC pipeline."""

    symbol: str
    timeframe: str
    years: int
    exchange_id: str
    initial_capital: float
    output_dir: Path
    equity_curve_filename: str
    strategy: Strategy


def load_config(path: Path | None = None) -> AppConfig:
    """
    Load configuration from YAML and apply environment overrides.

    Args:
        path: Path to config.yaml. Defaults to the project root config.yaml.

    Returns:
        Parsed AppConfig instance.

    Raises:
        FileNotFoundError: If the config file does not exist.
        ValueError: If required keys are missing or invalid.
    """
    # .env loads before YAML so DATABASE_URL is available to data.db on import paths.
    load_dotenv()
    config_path = path or DEFAULT_CONFIG_PATH
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open(encoding="utf-8") as handle:
        raw: dict[str, Any] = yaml.safe_load(handle)

    # POC only supports a single entry/exit leg; full DSL comes in a later phase.
    strategy = raw.get("strategy")
    if not strategy or "entry" not in strategy or "exit" not in strategy:
        raise ValueError("config.yaml must define strategy.entry and strategy.exit")

    return AppConfig(
        symbol=str(raw["symbol"]),
        timeframe=str(raw["timeframe"]),
        years=int(raw["years"]),
        exchange_id=str(raw["exchange_id"]),
        initial_capital=float(raw["initial_capital"]),
        output_dir=Path(str(raw.get("output_dir", "output"))),
        equity_curve_filename=str(raw.get("equity_curve_filename", "equity_curve.png")),
        strategy=strategy,
    )
