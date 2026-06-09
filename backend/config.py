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

from backtest.types import BacktestConfig, CommissionConfig, SizingConfig
from signals.types import DualStrategy, SideStrategy, Strategy

DEFAULT_CONFIG_PATH = Path(__file__).parent / "config.yaml"

DEFAULT_BACKTEST_SLIPPAGE_BPS = 0.0
DEFAULT_BACKTEST_COMMISSION_RATE = 0.0
PRODUCTION_BACKTEST_SLIPPAGE_BPS = 5.0
PRODUCTION_BACKTEST_COMMISSION_RATE = 0.001


@dataclass(frozen=True)
class AppConfig:
    """Runtime settings for the backtest pipeline."""

    symbol: str
    timeframe: str
    years: int
    exchange_id: str
    initial_capital: float
    output_dir: Path
    equity_curve_filename: str
    active_strategy: str
    strategy: Strategy | DualStrategy
    backtest: BacktestConfig


def is_dual_strategy(strategy: Strategy | DualStrategy) -> bool:
    """Return True when the strategy defines separate long and short legs."""
    return "long" in strategy and "short" in strategy


def get_strategy_benchmark(strategy: Strategy | DualStrategy) -> str:
    """Return per-strategy benchmark mode (symbol or none). Defaults to symbol."""
    return str(strategy.get("benchmark", "symbol"))


def _parse_commission(raw: dict[str, Any] | None) -> CommissionConfig:
    """Parse commission config with zero-fee defaults when absent."""
    if not raw:
        return CommissionConfig(type="percent", rate=0.0)
    commission_type = str(raw.get("type", "percent"))
    if commission_type not in {"percent", "flat"}:
        raise ValueError(f"Unsupported commission type: {commission_type}")
    return CommissionConfig(
        type=commission_type,  # type: ignore[arg-type]
        rate=float(raw.get("rate", DEFAULT_BACKTEST_COMMISSION_RATE)),
        amount=float(raw.get("amount", 0.0)),
    )


def _parse_sizing(raw: dict[str, Any] | None) -> SizingConfig:
    """Parse sizing config; defaults to full_capital."""
    if not raw:
        return SizingConfig()
    mode = str(raw.get("mode", "full_capital"))
    valid_modes = {"full_capital", "fixed_pct", "fixed_notional", "risk_pct"}
    if mode not in valid_modes:
        raise ValueError(f"Unsupported sizing mode: {mode}")
    return SizingConfig(
        mode=mode,  # type: ignore[arg-type]
        pct=float(raw.get("pct", 1.0)),
        amount=float(raw.get("amount", 0.0)),
        risk_pct=float(raw.get("risk_pct", 0.0)),
    )


def _parse_backtest(raw: dict[str, Any] | None, output_dir: Path) -> BacktestConfig:
    """
    Parse the global backtest block.

    When absent, uses zero slippage and zero commission so tests stay stable.
    """
    if not raw:
        return BacktestConfig(
            slippage_bps=DEFAULT_BACKTEST_SLIPPAGE_BPS,
            commission=CommissionConfig(type="percent", rate=DEFAULT_BACKTEST_COMMISSION_RATE),
            sizing=SizingConfig(),
            export_trades=True,
            trades_csv=output_dir / "trades.csv",
        )

    trades_csv = raw.get("trades_csv", "output/trades.csv")
    return BacktestConfig(
        slippage_bps=float(raw.get("slippage_bps", PRODUCTION_BACKTEST_SLIPPAGE_BPS)),
        commission=_parse_commission(raw.get("commission")),
        sizing=_parse_sizing(raw.get("sizing")),
        export_trades=bool(raw.get("export_trades", True)),
        trades_csv=Path(str(trades_csv)),
    )


def _validate_side_strategy(name: str, side: SideStrategy) -> None:
    """
    Validate per-side strategy config at startup (D-51).

    Raises:
        ValueError: If risk_pct sizing is configured without a stop_loss.
    """
    sizing = side.get("sizing")
    if not sizing:
        return
    if sizing.get("mode") == "risk_pct" and "stop_loss" not in side:
        raise ValueError(f"{name}: risk_pct sizing requires stop_loss (D-51)")


def _validate_strategy(name: str, strategy: Strategy | DualStrategy) -> None:
    """Validate strategy-level sizing and benchmark settings."""
    benchmark = strategy.get("benchmark", "symbol")
    if benchmark not in {"symbol", "none"}:
        raise ValueError(f"{name}: benchmark must be 'symbol' or 'none', got {benchmark!r}")

    if is_dual_strategy(strategy):
        _validate_side_strategy(f"{name}.long", strategy["long"])
        _validate_side_strategy(f"{name}.short", strategy["short"])
        return

    sizing = strategy.get("sizing")
    if sizing and sizing.get("mode") == "risk_pct":
        raise ValueError(f"{name}: risk_pct sizing on long-only strategies is not supported yet")


def _resolve_active_strategy(raw: dict[str, Any]) -> tuple[str, Strategy | DualStrategy]:
    """
    Resolve the active strategy from config.yaml.

    Supports the named `strategies` map with `active_strategy`, and falls back to
    a legacy top-level `strategy` block for older configs.
    """
    strategies = raw.get("strategies")
    if strategies:
        active_name = str(raw.get("active_strategy", "")).strip()
        if not active_name:
            raise ValueError("config.yaml must define active_strategy when strategies are present")
        if active_name not in strategies:
            known = ", ".join(sorted(strategies))
            raise ValueError(f"Unknown active_strategy '{active_name}'. Known strategies: {known}")
        strategy = strategies[active_name]
        _validate_strategy(active_name, strategy)
        return active_name, strategy

    strategy = raw.get("strategy")
    if not strategy or "entry" not in strategy or "exit" not in strategy:
        raise ValueError("config.yaml must define strategies or legacy strategy.entry and strategy.exit")
    _validate_strategy("legacy", strategy)
    return "legacy", strategy


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

    active_strategy, strategy = _resolve_active_strategy(raw)
    output_dir = Path(str(raw.get("output_dir", "output")))

    return AppConfig(
        symbol=str(raw["symbol"]),
        timeframe=str(raw["timeframe"]),
        years=int(raw["years"]),
        exchange_id=str(raw["exchange_id"]),
        initial_capital=float(raw["initial_capital"]),
        output_dir=output_dir,
        equity_curve_filename=str(raw.get("equity_curve_filename", "equity_curve.png")),
        active_strategy=active_strategy,
        strategy=strategy,
        backtest=_parse_backtest(raw.get("backtest"), output_dir),
    )
