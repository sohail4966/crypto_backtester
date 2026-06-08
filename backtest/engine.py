"""
Backtest engine with next-bar open fills (D-14 invariant).

Supports long-only or long/short strategies with optional ATR stop loss and
risk-reward take profit per side, plus slippage and commission (Phase 3).
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from backtest.fills import CostModel, FillModel
from backtest.types import BacktestConfig, ExitReason, PositionSide
from signals.types import SideStrategy, StopLossConfig, TakeProfitConfig

# Hardcoded invariant: signal on bar N fills at open of bar N+1 (see D-14).
ENTRY_ON_NEXT_BAR = True


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
    size: float = 0.0
    commission_paid: float = 0.0
    pnl_quote: float = 0.0


@dataclass
class _OpenPosition:
    """In-memory state for the current open position."""

    side: PositionSide
    entry_date: pd.Timestamp
    entry_fill: float
    position_notional: float
    entry_commission: float
    capital_before_trade: float
    stop_price: float = 0.0
    target_price: float = 0.0
    risk_active: bool = False


def _return_pct(side: PositionSide, entry_price: float, exit_price: float) -> float:
    """Compute signed percentage return for a closed position."""
    if side == "long":
        return ((exit_price / entry_price) - 1.0) * 100.0
    return ((entry_price / exit_price) - 1.0) * 100.0


def _proceeds(side: PositionSide, position_notional: float, entry_fill: float, exit_fill: float) -> float:
    """Compute quote proceeds before exit commission."""
    if side == "long":
        return position_notional * (exit_fill / entry_fill)
    return position_notional * (entry_fill / exit_fill)


def _mark_equity(
    candles: pd.DataFrame,
    bar_index: int,
    position: _OpenPosition | None,
    cash: float,
) -> float:
    """Mark portfolio equity at the close of the given bar."""
    if position is None:
        return cash

    close_price = float(candles.iloc[bar_index]["close"])
    return _proceeds(position.side, position.position_notional, position.entry_fill, close_price)


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
    position: _OpenPosition,
    raw_exit_price: float,
    exit_reason: ExitReason,
    fill_model: FillModel,
    cost_model: CostModel,
    trades: list[Trade],
    *,
    forced_close: bool = False,
) -> float:
    """Close the open position and append a completed trade. Returns cash."""
    exit_fill = fill_model.apply(raw_exit_price, position.side, is_entry=False)
    gross_proceeds = _proceeds(
        position.side,
        position.position_notional,
        position.entry_fill,
        exit_fill,
    )
    exit_commission = cost_model.compute(gross_proceeds)
    cash = gross_proceeds - exit_commission
    commission_paid = position.entry_commission + exit_commission
    pnl_quote = cash - position.capital_before_trade

    trades.append(
        Trade(
            entry_date=position.entry_date,
            exit_date=candles.iloc[bar_index]["ts"],
            entry_price=position.entry_fill,
            exit_price=exit_fill,
            return_pct=_return_pct(position.side, position.entry_fill, exit_fill),
            side=position.side,
            exit_reason=exit_reason,
            forced_close=forced_close,
            size=position.position_notional,
            commission_paid=commission_paid,
            pnl_quote=pnl_quote,
        )
    )
    return cash


def _enter_position(
    candles: pd.DataFrame,
    bar_index: int,
    side: PositionSide,
    cash: float,
    fill_model: FillModel,
    cost_model: CostModel,
    side_config: SideStrategy | None,
    atr_series: pd.Series | None,
    signal_bar: int,
) -> tuple[_OpenPosition, float]:
    """Open a new position and return position state with remaining cash (always 0 for full capital)."""
    raw_price = float(candles.iloc[bar_index]["open"])
    entry_fill = fill_model.apply(raw_price, side, is_entry=True)
    capital_before = cash
    entry_commission = cost_model.compute(capital_before)
    position_notional = capital_before - entry_commission

    position = _OpenPosition(
        side=side,
        entry_date=candles.iloc[bar_index]["ts"],
        entry_fill=entry_fill,
        position_notional=position_notional,
        entry_commission=entry_commission,
        capital_before_trade=capital_before,
    )

    if side_config is not None and atr_series is not None:
        atr_value = float(atr_series.iloc[signal_bar])
        if not pd.isna(atr_value):
            stop_price, target_price = _compute_risk_levels(
                entry_fill,
                side,
                atr_value,
                side_config["stop_loss"],
                side_config["take_profit"],
            )
            position.stop_price = stop_price
            position.target_price = target_price
            position.risk_active = True

    return position, 0.0


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
    backtest_config: BacktestConfig | None = None,
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
        backtest_config: Slippage and commission settings. Defaults to zero fees.

    Returns:
        Tuple of trade list and per-bar equity Series (attrs: initial/final capital,
        forced_close flag).
    """
    if not ENTRY_ON_NEXT_BAR:
        raise RuntimeError("ENTRY_ON_NEXT_BAR=False is not supported in the POC engine")

    config = backtest_config or BacktestConfig()
    fill_model = FillModel(config.slippage_bps)
    cost_model = CostModel(config.commission)
    dual_mode = short_entry_signals is not None and short_exit_signals is not None

    trades: list[Trade] = []
    position: _OpenPosition | None = None
    forced_close = False
    cash = initial_capital

    equity = pd.Series(index=candles.index, dtype=float)
    bar_count = len(candles)

    for bar_index in range(bar_count):
        if bar_index > 0:
            signal_bar = bar_index - 1

            if position is not None and position.risk_active:
                risk_exit = _check_risk_exit(
                    candles,
                    bar_index,
                    position.side,
                    position.stop_price,
                    position.target_price,
                )
                if risk_exit is not None:
                    raw_exit_price, exit_reason = risk_exit
                    cash = _close_position(
                        candles,
                        bar_index,
                        position,
                        raw_exit_price,
                        exit_reason,
                        fill_model,
                        cost_model,
                        trades,
                    )
                    position = None

            if position is not None and position.side == "long":
                if bool(exit_signals.iloc[signal_bar]):
                    raw_exit = float(candles.iloc[bar_index]["open"])
                    cash = _close_position(
                        candles,
                        bar_index,
                        position,
                        raw_exit,
                        "signal",
                        fill_model,
                        cost_model,
                        trades,
                    )
                    position = None
            elif (
                position is not None
                and position.side == "short"
                and dual_mode
                and short_exit_signals is not None
                and bool(short_exit_signals.iloc[signal_bar])
            ):
                raw_exit = float(candles.iloc[bar_index]["open"])
                cash = _close_position(
                    candles,
                    bar_index,
                    position,
                    raw_exit,
                    "signal",
                    fill_model,
                    cost_model,
                    trades,
                )
                position = None

            if position is None:
                if bool(entry_signals.iloc[signal_bar]):
                    position, cash = _enter_position(
                        candles,
                        bar_index,
                        "long",
                        cash,
                        fill_model,
                        cost_model,
                        long_side,
                        atr_series,
                        signal_bar,
                    )
                elif dual_mode and short_entry_signals is not None and bool(short_entry_signals.iloc[signal_bar]):
                    position, cash = _enter_position(
                        candles,
                        bar_index,
                        "short",
                        cash,
                        fill_model,
                        cost_model,
                        short_side,
                        atr_series,
                        signal_bar,
                    )

        equity.iloc[bar_index] = _mark_equity(candles, bar_index, position, cash)

    if position is not None:
        raw_exit = float(candles.iloc[-1]["close"])
        cash = _close_position(
            candles,
            bar_count - 1,
            position,
            raw_exit,
            "forced_close",
            fill_model,
            cost_model,
            trades,
            forced_close=True,
        )
        position = None
        forced_close = True
        equity.iloc[-1] = cash

    equity.attrs["forced_close"] = forced_close
    equity.attrs["final_capital"] = cash
    equity.attrs["initial_capital"] = initial_capital
    return trades, equity
