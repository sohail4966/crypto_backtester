"""
Stop loss, take profit, and trailing stop logic for the backtest engine (D-37, D-41).
"""

from __future__ import annotations

from dataclasses import dataclass

from backtest.types import ExitReason, PositionSide
from signals.types import StopLossConfig, TakeProfitConfig

_PRICE_EPS = 1e-9


def is_trailing_stop(stop_loss: StopLossConfig) -> bool:
    """Return True when the stop loss config uses a trailing ratchet."""
    return stop_loss.get("type") in {"atr_trail", "fixed_pct_trail"}


def compute_initial_stop(
    entry_fill: float,
    side: PositionSide,
    stop_loss: StopLossConfig,
    atr_value: float,
) -> float:
    """
    Compute the initial stop price at entry.

    Args:
        entry_fill: Entry fill price after slippage.
        side: Long or short.
        stop_loss: Stop loss configuration.
        atr_value: ATR at the signal bar (required for atr / atr_trail).

    Returns:
        Initial stop price.

    Raises:
        ValueError: If the stop type is unsupported or required inputs are missing.
    """
    stop_type = stop_loss["type"]

    if stop_type in {"atr", "atr_trail"}:
        multiplier = float(stop_loss["multiplier"])
        if side == "long":
            return entry_fill - (atr_value * multiplier)
        return entry_fill + (atr_value * multiplier)

    if stop_type == "fixed":
        if "price" in stop_loss:
            return float(stop_loss["price"])
        offset_pct = float(stop_loss["offset_pct"])
        if side == "long":
            return entry_fill * (1.0 - offset_pct)
        return entry_fill * (1.0 + offset_pct)

    if stop_type == "fixed_pct_trail":
        trail_pct = float(stop_loss["trail_pct"])
        if side == "long":
            return entry_fill * (1.0 - trail_pct)
        return entry_fill * (1.0 + trail_pct)

    raise ValueError(f"Unsupported stop_loss type: {stop_type}")


def compute_take_profit_target(
    entry_fill: float,
    side: PositionSide,
    take_profit: TakeProfitConfig,
    *,
    stop_price: float | None = None,
) -> float:
    """
    Compute the take profit price at entry.

    Args:
        entry_fill: Entry fill price after slippage.
        side: Long or short.
        take_profit: Take profit configuration.
        stop_price: Stop price (required for risk_reward).

    Returns:
        Target price.

    Raises:
        ValueError: If the take profit type is unsupported.
    """
    tp_type = take_profit["type"]

    if tp_type == "risk_reward":
        if stop_price is None:
            raise ValueError("risk_reward take profit requires stop_price")
        ratio = float(take_profit["ratio"])
        if side == "long":
            risk = entry_fill - stop_price
            return entry_fill + (risk * ratio)
        risk = stop_price - entry_fill
        return entry_fill - (risk * ratio)

    if tp_type == "fixed":
        if "price" in take_profit:
            return float(take_profit["price"])
        offset_pct = float(take_profit["offset_pct"])
        if side == "long":
            return entry_fill * (1.0 + offset_pct)
        return entry_fill * (1.0 - offset_pct)

    raise ValueError(f"Unsupported take_profit type: {tp_type}")


@dataclass
class RiskLevels:
    """Resolved intrabar risk exit levels for an open position."""

    stop_price: float
    target_price: float | None
    stop_is_trailing: bool
    take_profit_active: bool


def resolve_risk_levels(
    entry_fill: float,
    side: PositionSide,
    stop_loss: StopLossConfig | None,
    take_profit: TakeProfitConfig | None,
    atr_value: float | None,
) -> RiskLevels | None:
    """
    Build initial risk levels when stop and/or take profit are configured.

    Returns:
        RiskLevels when at least one of stop or take profit is present; else None.
    """
    if stop_loss is None and take_profit is None:
        return None

    stop_price = 0.0
    stop_is_trailing = False
    if stop_loss is not None:
        if atr_value is None and stop_loss["type"] in {"atr", "atr_trail"}:
            return None
        atr = atr_value if atr_value is not None else 0.0
        stop_price = compute_initial_stop(entry_fill, side, stop_loss, atr)
        stop_is_trailing = is_trailing_stop(stop_loss)

    target_price: float | None = None
    take_profit_active = False
    if take_profit is not None:
        target_price = compute_take_profit_target(
            entry_fill,
            side,
            take_profit,
            stop_price=stop_price if stop_loss is not None else entry_fill,
        )
        take_profit_active = True

    return RiskLevels(
        stop_price=stop_price,
        target_price=target_price,
        stop_is_trailing=stop_is_trailing,
        take_profit_active=take_profit_active,
    )


def update_trailing_stop(
    side: PositionSide,
    stop_price: float,
    trail_best_price: float,
    high: float,
    low: float,
    stop_loss: StopLossConfig,
    atr_value: float,
) -> tuple[float, float]:
    """
    Ratchet the trailing stop using the current bar's high/low.

    Returns:
        Updated (stop_price, trail_best_price).
    """
    stop_type = stop_loss["type"]

    if stop_type == "atr_trail":
        multiplier = float(stop_loss["multiplier"])
        if side == "long":
            trail_best_price = max(trail_best_price, high)
            candidate = trail_best_price - (atr_value * multiplier)
            return max(stop_price, candidate), trail_best_price
        trail_best_price = min(trail_best_price, low)
        candidate = trail_best_price + (atr_value * multiplier)
        return min(stop_price, candidate), trail_best_price

    if stop_type == "fixed_pct_trail":
        trail_pct = float(stop_loss["trail_pct"])
        if side == "long":
            trail_best_price = max(trail_best_price, high)
            candidate = trail_best_price * (1.0 - trail_pct)
            return max(stop_price, candidate), trail_best_price
        trail_best_price = min(trail_best_price, low)
        candidate = trail_best_price * (1.0 + trail_pct)
        return min(stop_price, candidate), trail_best_price

    return stop_price, trail_best_price


def check_intrabar_exit(
    side: PositionSide,
    high: float,
    low: float,
    stop_price: float,
    target_price: float | None,
    *,
    take_profit_active: bool,
    stop_is_trailing: bool,
    stop_loss_configured: bool,
) -> tuple[float, ExitReason] | None:
    """
    Check whether stop or take profit was hit on the current bar.

    Stop loss is checked before take profit when both could occur (D-37).
    """
    if stop_loss_configured:
        if side == "long" and low <= stop_price + _PRICE_EPS:
            reason: ExitReason = "trailing_stop" if stop_is_trailing else "stop_loss"
            return stop_price, reason
        if side == "short" and high >= stop_price - _PRICE_EPS:
            reason = "trailing_stop" if stop_is_trailing else "stop_loss"
            return stop_price, reason

    if take_profit_active and target_price is not None:
        if side == "long" and high >= target_price - _PRICE_EPS:
            return target_price, "take_profit"
        if side == "short" and low <= target_price + _PRICE_EPS:
            return target_price, "take_profit"

    return None
