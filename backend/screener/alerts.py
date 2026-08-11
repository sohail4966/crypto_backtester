"""
Alert events and console/log delivery (D-102, D-108).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from screener.types import ScanMatch

logger = logging.getLogger("screener.alerts")


@dataclass(frozen=True)
class AlertEvent:
    """A single alert fired by the screener."""

    symbol: str
    timeframe: str
    bar_ts: str
    message: str
    close: float | None = None


class AlertSink(Protocol):
    """Delivery sink for alert events."""

    def emit(self, event: AlertEvent) -> None:
        """Deliver one alert."""


class ConsoleAlertSink:
    """Log alerts at INFO (console-friendly for cron)."""

    def emit(self, event: AlertEvent) -> None:
        """Write an alert line via the standard logger."""
        close_part = f" close={event.close}" if event.close is not None else ""
        logger.info(
            "ALERT %s %s @ %s%s — %s",
            event.symbol,
            event.timeframe,
            event.bar_ts,
            close_part,
            event.message,
        )


def match_to_alert(match: ScanMatch, message: str = "condition matched") -> AlertEvent:
    """Build an AlertEvent from a ScanMatch."""
    return AlertEvent(
        symbol=match.symbol,
        timeframe=match.timeframe,
        bar_ts=match.bar_ts,
        message=message,
        close=match.close,
    )
