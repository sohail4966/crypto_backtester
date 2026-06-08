"""
Backtest engine with next-bar open fills (D-14 invariant).

Supports long-only or long/short strategies with optional ATR stop loss and
risk-reward take profit per side.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

from signals.types import SideStrategy, StopLossConfig, TakeProfitConfig

# Hardcoded invariant: signal on bar N fills at open of bar N+1 (see D-14).
ENTRY_ON_NEXT_BAR = True

PositionSide = Literal["long", "short"]
ExitReason = Literal["signal", "stop_loss", "take_profit", "forced_close"]


@dataclass
class Trade:
    """A single completed round-trip trade."""

    entry_date: pd.Timestamp
    exit_date: pd.Timestamp
    entry_price: float
    exit_price: float
    return_pct: float
    side: PositionSide = "long"
    exit_reason: ExitReason = "signal"
    forced_close: bool = False


def _return_pct(side: PositionSide, entry_price: float, exit_price: float) -> float:
    """Compute signed percentage return for a closed position."""
    if side == "long":
        return ((exit_price / entry_price) - 1.0) * 100.0
    return ((entry_price / exit_price) - 1.0) * 100.0


def _mark_equity(
    candles: pd.DataFrame,
    bar_index: int,
    side: PositionSide | None,
    entry_price: float,
    current_capital: float,
) -> float:
    """Mark portfolio equity at the close of the given bar."""
    if side is None:
        return current_capital

    close_price = float(candles.iloc[bar_index]["close"])
    if side == "long":
        return current_capital * (close_price / entry_price)
    return current_capital * (entry_price / close_price)


def _compute_risk_levels(
    entry_price: float,
    side: PositionSide,
    atr_value: float,
    stop_loss: StopLossConfig,
    take_profit: TakeProfitConfig,
) -> tuple[float, float]:
    """Derive stop loss and take profit prices from ATR risk and reward ratio."""
    if stop_loss["type"] != "atr":
        raise ValueError(f"Unsupported stop_loss type: {stop_loss['type']}")
    if take_profit["type"] != "risk_reward":
        raise ValueError(f"Unsupported take_profit type: {take_profit['type']}")

    multiplier = float(stop_loss["multiplier"])
    ratio = float(take_profit["ratio"])
    if side == "long":
        stop_price = entry_price - (atr_value * multiplier)
        risk = entry_price - stop_price
        target_price = entry_price + (risk * ratio)
        return stop_price, target_price

    stop_price = entry_price + (atr_value * multiplier)
    risk = stop_price - entry_price
    target_price = entry_price - (risk * ratio)
    return stop_price, target_price


def _check_risk_exit(
    candles: pd.DataFrame,
    bar_index: int,
    side: PositionSide,
    stop_price: float,
    target_price: float,
) -> tuple[float, ExitReason] | None:
    """
    Check whether stop loss or take profit was hit on the current bar.

    Stop loss is checked before take profit when both could occur on one bar.
    """
    bar = candles.iloc[bar_index]
    high = float(bar["high"])
    low = float(bar["low"])

    if side == "long":
        if low <= stop_price:
            return stop_price, "stop_loss"
        if high >= target_price:
            return target_price, "take_profit"
        return None

    if high >= stop_price:
        return stop_price, "stop_loss"
    if low <= target_price:
        return target_price, "take_profit"
    return None


def _close_position(
    candles: pd.DataFrame,
    bar_index: int,
    side: PositionSide,
    entry_price: float,
    entry_date: pd.Timestamp,
    current_capital: float,
    exit_price: float,
    exit_reason: ExitReason,
    trades: list[Trade],
    *,
    forced_close: bool = False,
) -> float:
    """Close the open position and append a completed trade."""
    exit_date = candles.iloc[bar_index]["ts"]
    if side == "long":
        current_capital *= exit_price / entry_price
    else:
        current_capital *= entry_price / exit_price

    trades.append(
        Trade(
            entry_date=entry_date,
            exit_date=exit_date,
            entry_price=entry_price,
            exit_price=exit_price,
            return_pct=_return_pct(side, entry_price, exit_price),
            side=side,
            exit_reason=exit_reason,
            forced_close=forced_close,
        )
    )
    return current_capital


def _try_signal_exit(
    candles: pd.DataFrame,
    bar_index: int,
    side: PositionSide,
    entry_price: float,
    entry_date: pd.Timestamp,
    current_capital: float,
    exit_signals: pd.Series,
    trades: list[Trade],
) -> tuple[PositionSide | None, float, pd.Timestamp | None, float]:
    """Exit on the prior bar's signal at the current bar's open."""
    signal_bar = bar_index - 1
    if not bool(exit_signals.iloc[signal_bar]):
        return side, entry_price, entry_date, current_capital

    exit_price = float(candles.iloc[bar_index]["open"])
    current_capital = _close_position(
        candles,
        bar_index,
        side,
        entry_price,
        entry_date,
        current_capital,
        exit_price,
        "signal",
        trades,
    )
    return None, 0.0, None, current_capital


def _open_position(
    side: PositionSide,
    entry_price: float,
    entry_date: pd.Timestamp,
    side_config: SideStrategy | None,
    atr_series: pd.Series | None,
    signal_bar: int,
) -> tuple[float, float] | None:
    """Compute stop/target levels for a new position, or None when ATR is unavailable."""
    if side_config is None or atr_series is None:
        return None

    atr_value = float(atr_series.iloc[signal_bar])
    if pd.isna(atr_value):
        return None

    return _compute_risk_levels(
        entry_price,
        side,
        atr_value,
        side_config["stop_loss"],
        side_config["take_profit"],
    )


def run_backtest(
    candles: pd.DataFrame,
    entry_signals: pd.Series,
    exit_signals: pd.Series,
    initial_capital: float,
    *,
    short_entry_signals: pd.Series | None = None,
    short_exit_signals: pd.Series | None = None,
    long_side: SideStrategy | None = None,
    short_side: SideStrategy | None = None,
    atr_series: pd.Series | None = None,
) -> tuple[list[Trade], pd.Series]:
    """
    Run a backtest with one position at a time and full capital sizing.

    Args:
        candles: OHLCV DataFrame with ts, open, high, low, close columns.
        entry_signals: Long entry boolean Series; True on bar N schedules entry at open[N+1].
        exit_signals: Long exit boolean Series; True on bar N schedules exit at open[N+1].
        initial_capital: Starting cash.
        short_entry_signals: Optional short entry boolean Series.
        short_exit_signals: Optional short exit boolean Series.
        long_side: Optional long risk config with stop_loss and take_profit.
        short_side: Optional short risk config with stop_loss and take_profit.
        atr_series: Optional ATR values aligned to candles for risk exits.

    Returns:
        Tuple of trade list and per-bar equity Series (attrs: initial/final capital,
        forced_close flag).
    """
    if not ENTRY_ON_NEXT_BAR:
        raise RuntimeError("ENTRY_ON_NEXT_BAR=False is not supported in the POC engine")

    dual_mode = short_entry_signals is not None and short_exit_signals is not None

    trades: list[Trade] = []
    side: PositionSide | None = None
    entry_price = 0.0
    entry_date: pd.Timestamp | None = None
    stop_price = 0.0
    target_price = 0.0
    risk_active = False
    forced_close = False
    current_capital = initial_capital

    equity = pd.Series(index=candles.index, dtype=float)
    bar_count = len(candles)

    for bar_index in range(bar_count):
        if bar_index > 0:
            signal_bar = bar_index - 1

            if side is not None and risk_active:
                risk_exit = _check_risk_exit(candles, bar_index, side, stop_price, target_price)
                if risk_exit is not None:
                    exit_price, exit_reason = risk_exit
                    current_capital = _close_position(
                        candles,
                        bar_index,
                        side,
                        entry_price,
                        entry_date,
                        current_capital,
                        exit_price,
                        exit_reason,
                        trades,
                    )
                    side = None
                    entry_date = None
                    risk_active = False

            if side == "long":
                side, entry_price, entry_date, current_capital = _try_signal_exit(
                    candles,
                    bar_index,
                    "long",
                    entry_price,
                    entry_date,
                    current_capital,
                    exit_signals,
                    trades,
                )
            elif side == "short" and dual_mode and short_exit_signals is not None:
                side, entry_price, entry_date, current_capital = _try_signal_exit(
                    candles,
                    bar_index,
                    "short",
                    entry_price,
                    entry_date,
                    current_capital,
                    short_exit_signals,
                    trades,
                )

            if side is None:
                if bool(entry_signals.iloc[signal_bar]):
                    entry_price = float(candles.iloc[bar_index]["open"])
                    entry_date = candles.iloc[bar_index]["ts"]
                    side = "long"
                    levels = _open_position("long", entry_price, entry_date, long_side, atr_series, signal_bar)
                    risk_active = levels is not None
                    if levels is not None:
                        stop_price, target_price = levels
                elif dual_mode and short_entry_signals is not None and bool(short_entry_signals.iloc[signal_bar]):
                    entry_price = float(candles.iloc[bar_index]["open"])
                    entry_date = candles.iloc[bar_index]["ts"]
                    side = "short"
                    levels = _open_position("short", entry_price, entry_date, short_side, atr_series, signal_bar)
                    risk_active = levels is not None
                    if levels is not None:
                        stop_price, target_price = levels

        equity.iloc[bar_index] = _mark_equity(candles, bar_index, side, entry_price, current_capital)

    if side is not None:
        last = candles.iloc[-1]
        exit_price = float(last["close"])
        current_capital = _close_position(
            candles,
            bar_count - 1,
            side,
            entry_price,
            entry_date,
            current_capital,
            exit_price,
            "forced_close",
            trades,
            forced_close=True,
        )
        forced_close = True
        equity.iloc[-1] = current_capital

    equity.attrs["forced_close"] = forced_close
    equity.attrs["final_capital"] = current_capital
    equity.attrs["initial_capital"] = initial_capital
    return trades, equity
