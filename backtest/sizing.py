"""
Position sizing calculations for the backtest engine (D-40).
"""

from __future__ import annotations

from backtest.types import PositionSide, SizingConfig
from signals.types import SideStrategy, StopLossConfig, SizingConfig as StrategySizingDict


def resolve_sizing(
    global_sizing: SizingConfig,
    side_config: SideStrategy | None,
) -> SizingConfig:
    """
    Resolve sizing for a trade side.

    Per-side strategy sizing overrides the global backtest defaults.
    """
    if side_config is None or "sizing" not in side_config:
        return global_sizing

    raw: StrategySizingDict = side_config["sizing"]
    mode = str(raw.get("mode", global_sizing.mode))
    return SizingConfig(
        mode=mode,  # type: ignore[arg-type]
        pct=float(raw.get("pct", global_sizing.pct)),
        amount=float(raw.get("amount", global_sizing.amount)),
        risk_pct=float(raw.get("risk_pct", global_sizing.risk_pct)),
    )


def _stop_distance(entry_fill: float, side: PositionSide, atr_value: float, stop_loss: StopLossConfig) -> float:
    """Return absolute price distance from entry to the ATR stop."""
    multiplier = float(stop_loss["multiplier"])
    if side == "long":
        return atr_value * multiplier
    return atr_value * multiplier


def compute_position_notional(
    sizing: SizingConfig,
    equity: float,
    entry_fill: float,
    side: PositionSide,
    *,
    atr_value: float | None = None,
    stop_loss: StopLossConfig | None = None,
) -> float:
    """
    Compute quote-currency notional to allocate for a new position.

    Args:
        sizing: Resolved sizing configuration.
        equity: Total account equity at entry (cash when flat).
        entry_fill: Entry fill price after slippage.
        side: Long or short.
        atr_value: ATR at the signal bar (required for risk_pct).
        stop_loss: Stop loss config (required for risk_pct).

    Returns:
        Notional in quote currency, or 0.0 when entry should be skipped.

    Raises:
        ValueError: If risk_pct is configured without ATR stop inputs.
    """
    if equity <= 0.0:
        return 0.0

    if sizing.mode == "full_capital":
        return equity

    if sizing.mode == "fixed_pct":
        return equity * sizing.pct

    if sizing.mode == "fixed_notional":
        return sizing.amount if sizing.amount <= equity else 0.0

    if sizing.mode == "risk_pct":
        if atr_value is None or stop_loss is None or stop_loss.get("type") != "atr":
            raise ValueError("risk_pct sizing requires an ATR stop_loss (D-51)")
        distance = _stop_distance(entry_fill, side, atr_value, stop_loss)
        if distance <= 0.0:
            return 0.0
        risk_amount = equity * sizing.risk_pct
        return risk_amount * entry_fill / distance

    raise ValueError(f"Unsupported sizing mode: {sizing.mode}")
