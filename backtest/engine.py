"""
Long-only backtest engine with next-bar open fills (D-14 invariant).

Executes entries and exits on the bar after the signal fires to avoid look-ahead bias.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

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
    forced_close: bool = False


def _apply_signals_for_bar(
    candles: pd.DataFrame,
    bar_index: int,
    in_position: bool,
    entry_price: float,
    entry_date: pd.Timestamp | None,
    current_capital: float,
    entry_signals: pd.Series,
    exit_signals: pd.Series,
    trades: list[Trade],
) -> tuple[bool, float, pd.Timestamp | None, float]:
    """
    Process exit and entry signals for the current bar.

    Args:
        candles: OHLCV DataFrame.
        bar_index: Index of the execution bar (fill bar).
        in_position: Whether a position is currently open.
        entry_price: Price at which the open position was entered.
        entry_date: Timestamp of entry.
        current_capital: Cash equity after closed trades.
        entry_signals: Boolean entry series indexed like candles.
        exit_signals: Boolean exit series indexed like candles.
        trades: Mutable list to append closed trades.

    Returns:
        Updated (in_position, entry_price, entry_date, current_capital).
    """
    # Signal fires on the prior bar's close; fill happens on this bar's open (D-14).
    signal_bar = bar_index - 1

    if in_position and bool(exit_signals.iloc[signal_bar]):
        exit_price = float(candles.iloc[bar_index]["open"])
        exit_date = candles.iloc[bar_index]["ts"]
        current_capital *= exit_price / entry_price
        trades.append(
            Trade(
                entry_date=entry_date,
                exit_date=exit_date,
                entry_price=entry_price,
                exit_price=exit_price,
                return_pct=((exit_price / entry_price) - 1.0) * 100.0,
            )
        )
        in_position = False
        entry_date = None

    # Exit before entry on the same bar so a flip does not stack two positions.
    if not in_position and bool(entry_signals.iloc[signal_bar]):
        entry_price = float(candles.iloc[bar_index]["open"])
        entry_date = candles.iloc[bar_index]["ts"]
        in_position = True

    return in_position, entry_price, entry_date, current_capital


def _mark_equity(
    candles: pd.DataFrame,
    bar_index: int,
    in_position: bool,
    entry_price: float,
    current_capital: float,
) -> float:
    """
    Mark portfolio equity at the close of the given bar.

    Args:
        candles: OHLCV DataFrame.
        bar_index: Bar index to mark.
        in_position: Whether a position is open.
        entry_price: Entry price of the open position.
        current_capital: Cash equity after closed trades.

    Returns:
        Mark-to-market equity for the bar.
    """
    if in_position:
        # Mark-to-market at close for the equity curve between trade exits.
        close_price = float(candles.iloc[bar_index]["close"])
        return current_capital * (close_price / entry_price)
    return current_capital


def _force_close_position(
    candles: pd.DataFrame,
    entry_price: float,
    entry_date: pd.Timestamp | None,
    current_capital: float,
    trades: list[Trade],
) -> float:
    """
    Close an open position at the last bar's close when no next bar exists.

    Args:
        candles: OHLCV DataFrame.
        entry_price: Entry price of the open position.
        entry_date: Entry timestamp.
        current_capital: Cash equity before this close.
        trades: Mutable list to append the forced trade.

    Returns:
        Updated capital after the forced close.
    """
    last = candles.iloc[-1]
    # No bar N+1 exists — close at last close, not next open (documented in metrics).
    exit_price = float(last["close"])
    current_capital *= exit_price / entry_price
    trades.append(
        Trade(
            entry_date=entry_date,
            exit_date=last["ts"],
            entry_price=entry_price,
            exit_price=exit_price,
            return_pct=((exit_price / entry_price) - 1.0) * 100.0,
            forced_close=True,
        )
    )
    return current_capital


def run_backtest(
    candles: pd.DataFrame,
    entry_signals: pd.Series,
    exit_signals: pd.Series,
    initial_capital: float,
) -> tuple[list[Trade], pd.Series]:
    """
    Run a long-only backtest with one position at a time and full capital sizing.

    Args:
        candles: OHLCV DataFrame with ts, open, high, low, close columns.
        entry_signals: Boolean Series; True on bar N schedules entry at open[N+1].
        exit_signals: Boolean Series; True on bar N schedules exit at open[N+1].
        initial_capital: Starting cash.

    Returns:
        Tuple of trade list and per-bar equity Series (attrs: initial/final capital,
        forced_close flag).
    """
    if not ENTRY_ON_NEXT_BAR:
        raise RuntimeError("ENTRY_ON_NEXT_BAR=False is not supported in the POC engine")

    trades: list[Trade] = []
    in_position = False
    entry_price = 0.0
    entry_date: pd.Timestamp | None = None
    forced_close = False
    current_capital = initial_capital

    equity = pd.Series(index=candles.index, dtype=float)
    bar_count = len(candles)

    for bar_index in range(bar_count):
        # Bar 0 has no prior signal bar, so fills cannot occur until index 1.
        if bar_index > 0:
            in_position, entry_price, entry_date, current_capital = _apply_signals_for_bar(
                candles,
                bar_index,
                in_position,
                entry_price,
                entry_date,
                current_capital,
                entry_signals,
                exit_signals,
                trades,
            )
        equity.iloc[bar_index] = _mark_equity(
            candles, bar_index, in_position, entry_price, current_capital
        )

    if in_position:
        current_capital = _force_close_position(
            candles, entry_price, entry_date, current_capital, trades
        )
        forced_close = True
        # Cash equity after forced close replaces the last mark-to-market point.
        equity.iloc[-1] = current_capital

    # attrs let metrics.py stay free of extra parameters (POC simplicity).
    equity.attrs["forced_close"] = forced_close
    equity.attrs["final_capital"] = current_capital
    equity.attrs["initial_capital"] = initial_capital
    return trades, equity
