"""
SMC types: concepts, sides, events, and aggregate results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

import pandas as pd


class SmcSide(StrEnum):
    """Directional bias of an SMC event."""

    BULLISH = "bullish"
    BEARISH = "bearish"


class SmcConcept(StrEnum):
    """Named SMC detector concepts (signal condition values)."""

    BOS = "bos"
    CHOCH = "choch"
    FVG = "fvg"
    ORDER_BLOCK = "order_block"
    LIQUIDITY_SWEEP = "liquidity_sweep"
    BREAKER_BLOCK = "breaker_block"
    MITIGATION_BLOCK = "mitigation_block"


class FvgInvalidation(StrEnum):
    """When a Fair Value Gap is considered filled / invalidated (D-97)."""

    TOUCH = "touch"
    MIDPOINT = "midpoint"
    FULL_FILL = "full_fill"


@dataclass(frozen=True)
class SmcEvent:
    """A single SMC detection event on a candle series."""

    concept: SmcConcept
    side: SmcSide
    index: int
    ts: pd.Timestamp
    price: float
    meta: dict = field(default_factory=dict)


@dataclass
class SmcResult:
    """Full SMC analysis output for one OHLCV series."""

    events: list[SmcEvent]
    config: object  # SmcConfig; avoid circular import at type time

    def events_for(
        self,
        concept: SmcConcept | str,
        side: SmcSide | str | None = None,
    ) -> list[SmcEvent]:
        """Filter events by concept and optional side."""
        concept_val = SmcConcept(concept)
        side_val = SmcSide(side) if side is not None else None
        out: list[SmcEvent] = []
        for event in self.events:
            if event.concept is not concept_val:
                continue
            if side_val is not None and event.side is not side_val:
                continue
            out.append(event)
        return out

    def series_for(
        self,
        index: pd.DatetimeIndex | pd.Index,
        concept: SmcConcept | str,
        side: str = "any",
    ) -> pd.Series:
        """
        Boolean Series True on event bars for ``concept``.

        Args:
            index: Candle index (DatetimeIndex preferred).
            concept: SMC concept name.
            side: ``bullish``, ``bearish``, or ``any``.
        """
        concept_val = SmcConcept(concept)
        flags = pd.Series(False, index=index)
        for event in self.events:
            if event.concept is not concept_val:
                continue
            if side in ("bullish", "bearish") and event.side.value != side:
                continue
            if 0 <= event.index < len(flags):
                flags.iloc[event.index] = True
        return flags
