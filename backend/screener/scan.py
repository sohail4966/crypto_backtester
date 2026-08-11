"""
Multi-symbol / multi-timeframe scan loop.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

import pandas as pd

from exceptions import InvalidSignalError
from screener.alerts import AlertSink, ConsoleAlertSink, match_to_alert
from screener.evaluate import collect_condition_timeframes
from screener.types import AlertTrigger, ScanMatch, ScanRequest, ScanResult
from signals.evaluator import apply_entry_trigger, evaluate_condition
from signals.types import SignalCondition

CandleLoader = Callable[[str, str, str, str], pd.DataFrame]


def _last_bar_match(
    candles: pd.DataFrame,
    triggered: pd.Series,
) -> ScanMatch | None:
    """Return a ScanMatch when the last closed bar is True."""
    if candles.empty or triggered.empty:
        return None
    if not bool(triggered.iloc[-1]):
        return None
    if "ts" in candles.columns:
        ts = candles["ts"].iloc[-1]
    else:
        ts = candles.index[-1]
    bar_ts = pd.Timestamp(ts).isoformat()
    close = float(candles["close"].iloc[-1]) if "close" in candles.columns else None
    return ScanMatch(
        symbol="",
        timeframe="",
        bar_ts=bar_ts,
        triggered=True,
        close=close,
    )


def scan_symbol_timeframe(
    symbol: str,
    timeframe: str,
    start: str,
    end: str,
    condition: SignalCondition,
    *,
    alert_trigger: AlertTrigger = "edge",
    loader: CandleLoader,
    extra_tfs: Sequence[str] = (),
) -> ScanMatch | None:
    """
    Evaluate one (symbol, timeframe) pair; return a match on last-bar trigger.

    Loads the base TF plus any extra / condition-referenced frames for MTF legs.
    """
    candles = loader(symbol, timeframe, start, end)
    if candles.empty:
        return None

    needed = set(extra_tfs) | collect_condition_timeframes(dict(condition))
    needed.discard(timeframe)
    frames: dict[str, pd.DataFrame] = {}
    for tf in needed:
        frame = loader(symbol, tf, start, end)
        if not frame.empty:
            frames[tf] = frame

    level = evaluate_condition(
        candles,
        condition,
        base_timeframe=timeframe,
        frames=frames or None,
    )
    triggered = apply_entry_trigger(level, alert_trigger)
    match = _last_bar_match(candles, triggered)
    if match is None:
        return None
    return ScanMatch(
        symbol=symbol,
        timeframe=timeframe,
        bar_ts=match.bar_ts,
        triggered=True,
        close=match.close,
    )


def run_multi_symbol_scan(
    request: ScanRequest,
    *,
    loader: CandleLoader,
    sink: AlertSink | None = None,
) -> ScanResult:
    """
    Scan every (symbol, timeframe) in the request.

    Args:
        request: Scan parameters.
        loader: ``get_candles``-compatible loader (injectable for tests).
        sink: Alert delivery sink; defaults to ConsoleAlertSink.

    Returns:
        ScanResult with matches, errors, and timing.
    """
    alert_sink = sink or ConsoleAlertSink()
    started = time.perf_counter()
    matches: list[ScanMatch] = []
    errors: list[dict[str, str]] = []
    scanned = 0

    if not request.timeframes:
        raise InvalidSignalError("Scan requires at least one timeframe")
    if not request.symbols:
        raise InvalidSignalError("Scan requires at least one symbol")

    for symbol in request.symbols:
        for timeframe in request.timeframes:
            scanned += 1
            try:
                match = scan_symbol_timeframe(
                    symbol,
                    timeframe,
                    request.start,
                    request.end,
                    request.condition,
                    alert_trigger=request.alert_trigger,
                    loader=loader,
                    extra_tfs=request.extra_frames,
                )
            except Exception as exc:  # noqa: BLE001 — isolate per pair
                errors.append(
                    {
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "error": str(exc),
                    }
                )
                continue
            if match is not None:
                matches.append(match)
                alert_sink.emit(match_to_alert(match))

    duration_ms = int((time.perf_counter() - started) * 1000)
    return ScanResult(
        matches=matches,
        alert_count=len(matches),
        duration_ms=duration_ms,
        scanned_pairs=scanned,
        condition=dict(request.condition),
        alert_trigger=request.alert_trigger,
        errors=errors,
    )


def condition_timeframes_from_mapping(condition: Mapping[str, Any]) -> set[str]:
    """Public helper wrapping collect_condition_timeframes."""
    return collect_condition_timeframes(dict(condition))
