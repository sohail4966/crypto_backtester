"""
Typed structures for the signal dict schema.
"""

from __future__ import annotations

from typing import Literal, NotRequired, TypedDict

EntryTrigger = Literal["edge", "level"]


class IndicatorRef(TypedDict, total=False):
    """Reference to another indicator series for cross-comparisons."""

    indicator: str
    params: NotRequired[dict[str, int | float | str]]


class SignalCondition(TypedDict, total=False):
    """A single indicator-based condition or an AND group of conditions."""

    indicator: str
    op: str
    value: float
    params: NotRequired[dict[str, int | float | str]]
    compare: str | IndicatorRef
    all: list["SignalCondition"]


class StopLossConfig(TypedDict, total=False):
    """
    Stop loss configuration.

    Types: atr, fixed, atr_trail, fixed_pct_trail.
    """

    type: str
    period: int
    multiplier: float
    offset_pct: float
    price: float
    trail_pct: float


class TakeProfitConfig(TypedDict, total=False):
    """
    Take profit configuration.

    Types: risk_reward, fixed.
    """

    type: str
    ratio: float
    offset_pct: float
    price: float


class SizingConfig(TypedDict, total=False):
    """
    Position sizing configuration.

    Modes: full_capital, fixed_pct, fixed_notional, risk_pct.
    """

    mode: str
    pct: float
    amount: float
    risk_pct: float


class SideStrategy(TypedDict, total=False):
    """Entry, exit, risk management, and sizing for one trade direction."""

    entry: SignalCondition
    exit: SignalCondition
    stop_loss: StopLossConfig
    take_profit: TakeProfitConfig
    sizing: SizingConfig


class Strategy(TypedDict, total=False):
    """Long-only strategy with separate entry and exit conditions."""

    benchmark: str
    entry_trigger: EntryTrigger
    entry: SignalCondition
    exit: SignalCondition
    sizing: SizingConfig


class DualStrategy(TypedDict, total=False):
    """Long and short strategy with per-side risk management."""

    benchmark: str
    entry_trigger: EntryTrigger
    long: SideStrategy
    short: SideStrategy
