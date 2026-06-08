"""
Typed structures for the signal dict schema.
"""

from __future__ import annotations

from typing import NotRequired, TypedDict


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


class StopLossConfig(TypedDict):
    """ATR-based stop loss applied at entry."""

    type: str
    period: int
    multiplier: float


class TakeProfitConfig(TypedDict):
    """Risk-reward take profit relative to stop distance."""

    type: str
    ratio: float


class SideStrategy(TypedDict):
    """Entry, exit, and risk management for one trade direction."""

    entry: SignalCondition
    exit: SignalCondition
    stop_loss: StopLossConfig
    take_profit: TakeProfitConfig


class Strategy(TypedDict):
    """Long-only strategy with separate entry and exit conditions."""

    entry: SignalCondition
    exit: SignalCondition


class DualStrategy(TypedDict):
    """Long and short strategy with per-side risk management."""

    long: SideStrategy
    short: SideStrategy
