"""
Typed structures for the Phase 8 screener.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from signals.types import EntryTrigger, SignalCondition

AlertTrigger = EntryTrigger  # edge | level (D-102)


@dataclass(frozen=True)
class ScanMatch:
    """One symbol×timeframe that matched on the last closed bar."""

    symbol: str
    timeframe: str
    bar_ts: str
    triggered: bool
    close: float | None = None


@dataclass
class ScanRequest:
    """Parameters for a multi-symbol / multi-TF scan."""

    symbols: list[str]
    timeframes: list[str]
    start: str
    end: str
    condition: SignalCondition
    alert_trigger: AlertTrigger = "edge"
    # When set, also load these TFs for cross-TF leaf conditions.
    extra_frames: list[str] = field(default_factory=list)


@dataclass
class ScanResult:
    """Outcome of a screener run."""

    matches: list[ScanMatch]
    alert_count: int
    duration_ms: int
    scanned_pairs: int
    condition: dict[str, Any]
    alert_trigger: Literal["edge", "level"]
    errors: list[dict[str, str]] = field(default_factory=list)
