"""
Market structure types: swings, labels, trend, and aggregate results.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import pandas as pd


class SwingKind(StrEnum):
    """Whether a swing is a pivot high or pivot low."""

    HIGH = "high"
    LOW = "low"


class SwingLabel(StrEnum):
    """Structural label of a swing versus the prior swing of the same kind."""

    FIRST = "first"
    HH = "HH"
    HL = "HL"
    LH = "LH"
    LL = "LL"
    EQH = "EQH"
    EQL = "EQL"


class Trend(StrEnum):
    """Market structure trend state derived from confirmed swings."""

    UPTREND = "uptrend"
    DOWNTREND = "downtrend"
    RANGE = "range"
    UNDEFINED = "undefined"


@dataclass(frozen=True)
class SwingPoint:
    """A detected swing high or low on an OHLCV series."""

    index: int
    ts: pd.Timestamp
    price: float
    kind: SwingKind
    label: SwingLabel
    confirmed: bool
    confirmation_index: int | None


@dataclass(frozen=True)
class StructureLevels:
    """
    Discrete support and resistance from recent confirmed swings.

    Lists are most-recent-first (index 0 = newest swing), not price-sorted.
    """

    support: list[float]
    resistance: list[float]


@dataclass(frozen=True)
class StructureResult:
    """Full single-timeframe structure analysis output."""

    swings: list[SwingPoint]
    levels: StructureLevels
    trend: pd.Series
