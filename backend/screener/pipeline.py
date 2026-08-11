"""
High-level screener pipeline entrypoint.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import pandas as pd

from screener.alerts import AlertSink
from screener.scan import run_multi_symbol_scan
from screener.types import AlertTrigger, ScanRequest, ScanResult
from signals.types import SignalCondition

CandleLoader = Callable[[str, str, str, str], pd.DataFrame]


def run_scan(
    *,
    symbols: Sequence[str],
    timeframes: Sequence[str],
    start: str,
    end: str,
    condition: SignalCondition | dict,
    alert_trigger: AlertTrigger = "edge",
    loader: CandleLoader | None = None,
    sink: AlertSink | None = None,
    extra_frames: Sequence[str] = (),
) -> ScanResult:
    """
    Run a multi-symbol / multi-TF screener pass.

    Args:
        symbols: Symbols to scan.
        timeframes: Timeframes to evaluate independently.
        start: Inclusive ISO start date.
        end: Inclusive ISO end date.
        condition: Signal condition tree.
        alert_trigger: ``edge`` (default) or ``level``.
        loader: Candle loader; defaults to ``data.loader.get_candles``.
        sink: Alert sink; defaults to console/log.
        extra_frames: Additional TFs to preload for cross-TF leaves.

    Returns:
        ScanResult with matches and timing.
    """
    if loader is None:
        from data.loader import get_candles

        loader = get_candles

    request = ScanRequest(
        symbols=list(symbols),
        timeframes=list(timeframes),
        start=start,
        end=end,
        condition=condition,  # type: ignore[arg-type]
        alert_trigger=alert_trigger,
        extra_frames=list(extra_frames),
    )
    return run_multi_symbol_scan(request, loader=loader, sink=sink)
