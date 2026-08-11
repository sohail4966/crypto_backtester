"""
Screener & alert engine (Phase 8).

Multi-symbol / multi-timeframe scans over signal condition trees.
"""

from __future__ import annotations

from screener.alerts import AlertEvent, ConsoleAlertSink
from screener.pipeline import run_scan
from screener.types import ScanMatch, ScanRequest, ScanResult

__all__ = [
    "AlertEvent",
    "ConsoleAlertSink",
    "ScanMatch",
    "ScanRequest",
    "ScanResult",
    "run_scan",
]
