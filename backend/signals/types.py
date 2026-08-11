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
    bars_ago: NotRequired[int]


class FieldRef(TypedDict, total=False):
    """OHLCV field reference with optional lookback."""

    field: str
    bars_ago: NotRequired[int]


class SignalCondition(TypedDict, total=False):
    """
    A condition leaf or group (Phase 9 DSL).

    Groups: ``op`` in AND/OR/NOT/SEQUENCE + ``conditions``, or legacy ``all``.
    Leaves: ``indicator``, ``field``, ``smc``, or ``pattern``.
    """

    indicator: str
    field: str
    op: str
    value: float
    params: NotRequired[dict[str, int | float | str]]
    compare: str | IndicatorRef
    ref: FieldRef | IndicatorRef
    bars_ago: NotRequired[int]
    timeframe: NotRequired[str]
    all: list["SignalCondition"]
    any: list["SignalCondition"]
    # ``not`` is a reserved keyword — use dict key "not" at runtime (Phase 8 D-105).
    conditions: list["SignalCondition"]
    within_bars: NotRequired[int]
    # Phase 7 SMC named conditions (D-98)
    smc: str
    side: str
    # Phase 9 pattern named conditions
    pattern: str


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

    schema_version: str
    benchmark: str
    entry_trigger: EntryTrigger
    entry: SignalCondition
    exit: SignalCondition
    sizing: SizingConfig


class DualStrategy(TypedDict, total=False):
    """Long and short strategy with per-side risk management."""

    schema_version: str
    benchmark: str
    entry_trigger: EntryTrigger
    long: SideStrategy
    short: SideStrategy
