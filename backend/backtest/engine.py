"""
Backtest engine with next-bar open fills (D-14 invariant).

Supports long-only or long/short strategies with optional risk exits, slippage,
commission, and position sizing (Phase 3).
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from backtest.fills import CostModel, FillModel
from backtest.risk import check_intrabar_exit, resolve_risk_levels, update_trailing_stop
from backtest.sizing import compute_position_notional, resolve_sizing
from backtest.types import BacktestConfig, ExitReason, PositionSide
from signals.types import SideStrategy, StopLossConfig

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
    equity_at_entry: float
    cash_reserve: float
    entry_bar_index: int
    stop_price: float = 0.0
    target_price: float | None = None
    risk_active: bool = False
    stop_is_trailing: bool = False
    stop_loss_configured: bool = False
    take_profit_active: bool = False
    trail_best_price: float = 0.0
    stop_loss_config: StopLossConfig | None = None


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
    position_value = _proceeds(position.side, position.position_notional, position.entry_fill, close_price)
    return position.cash_reserve + position_value


def _entry_cost(notional: float, cost_model: CostModel) -> tuple[float, float]:
    """Return (entry_commission, total_cash_debit) for opening a position."""
    commission = cost_model.compute(notional)
    return commission, notional + commission


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
    """Close the open position and append a completed trade. Returns total cash."""
    exit_fill = fill_model.apply(raw_exit_price, position.side, is_entry=False)
    gross_proceeds = _proceeds(
        position.side,
        position.position_notional,
        position.entry_fill,
        exit_fill,
    )
    exit_commission = cost_model.compute(gross_proceeds)
    cash = position.cash_reserve + gross_proceeds - exit_commission
    commission_paid = position.entry_commission + exit_commission
    cost_basis = position.position_notional + position.entry_commission
    pnl_quote = (gross_proceeds - exit_commission) - cost_basis

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


def _apply_risk_to_position(
    position: _OpenPosition,
    side_config: SideStrategy | None,
    atr_value: float | None,
) -> None:
    """Attach stop/target levels to a newly opened position."""
    if side_config is None:
        return

    levels = resolve_risk_levels(
        position.entry_fill,
        position.side,
        side_config.get("stop_loss"),
        side_config.get("take_profit"),
        atr_value,
    )
    if levels is None:
        return

    position.stop_price = levels.stop_price
    position.target_price = levels.target_price
    position.stop_is_trailing = levels.stop_is_trailing
    position.take_profit_active = levels.take_profit_active
    position.stop_loss_configured = side_config.get("stop_loss") is not None
    position.risk_active = position.stop_loss_configured or position.take_profit_active
    position.trail_best_price = position.entry_fill
    position.stop_loss_config = side_config.get("stop_loss")


def _maybe_update_trailing(
    position: _OpenPosition,
    candles: pd.DataFrame,
    bar_index: int,
    atr_series: pd.Series | None,
    signal_bar: int,
) -> None:
    """Ratchet trailing stops from the bar after entry (D-41)."""
    if not position.risk_active or not position.stop_is_trailing:
        return
    if bar_index <= position.entry_bar_index:
        return
    if position.stop_loss_config is None or atr_series is None:
        return

    atr_value = float(atr_series.iloc[signal_bar])
    if pd.isna(atr_value):
        return

    bar = candles.iloc[bar_index]
    position.stop_price, position.trail_best_price = update_trailing_stop(
        position.side,
        position.stop_price,
        position.trail_best_price,
        float(bar["high"]),
        float(bar["low"]),
        position.stop_loss_config,
        atr_value,
    )


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
    backtest_config: BacktestConfig,
) -> tuple[_OpenPosition | None, float]:
    """
    Open a new position when sizing allows.

    Returns:
        Tuple of position state (or None if skipped) and remaining cash.
    """
    raw_price = float(candles.iloc[bar_index]["open"])
    entry_fill = fill_model.apply(raw_price, side, is_entry=True)
    equity_at_entry = cash

    sizing = resolve_sizing(backtest_config.sizing, side_config)
    atr_value: float | None = None
    stop_loss: StopLossConfig | None = None
    if side_config is not None and atr_series is not None and "stop_loss" in side_config:
        raw_atr = float(atr_series.iloc[signal_bar])
        if not pd.isna(raw_atr):
            atr_value = raw_atr
            stop_loss = side_config["stop_loss"]

    try:
        if sizing.mode == "full_capital":
            entry_commission = cost_model.compute(equity_at_entry)
            notional = equity_at_entry - entry_commission
            total_debit = equity_at_entry
        else:
            notional = compute_position_notional(
                sizing,
                equity_at_entry,
                entry_fill,
                side,
                atr_value=atr_value,
                stop_loss=stop_loss,
            )
            if notional <= 0.0:
                return None, cash
            entry_commission, total_debit = _entry_cost(notional, cost_model)
    except ValueError:
        return None, cash

    if notional <= 0.0 or total_debit > equity_at_entry:
        return None, cash

    position = _OpenPosition(
        side=side,
        entry_date=candles.iloc[bar_index]["ts"],
        entry_fill=entry_fill,
        position_notional=notional,
        entry_commission=entry_commission,
        equity_at_entry=equity_at_entry,
        cash_reserve=equity_at_entry - total_debit,
        entry_bar_index=bar_index,
    )
    _apply_risk_to_position(position, side_config, atr_value)

    return position, position.cash_reserve


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
    Run a backtest with one position at a time and configurable position sizing.

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
        backtest_config: Slippage, commission, and sizing settings.

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
                _maybe_update_trailing(position, candles, bar_index, atr_series, signal_bar)
                bar = candles.iloc[bar_index]
                risk_exit = check_intrabar_exit(
                    position.side,
                    float(bar["high"]),
                    float(bar["low"]),
                    position.stop_price,
                    position.target_price,
                    take_profit_active=position.take_profit_active,
                    stop_is_trailing=position.stop_is_trailing,
                    stop_loss_configured=position.stop_loss_configured,
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
                        config,
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
                        config,
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
