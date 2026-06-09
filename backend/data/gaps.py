"""
Gap detection and reconciliation for canonical 1m candles.

Detects missing candle ranges from stored candle continuity, persists them in
data_gaps, and resolves recorded gaps once their candles have been backfilled.
Detection is pure logic kept out of the repository layer (which stays thin SQL);
persistence goes through GapRepository.

Policy: gaps are never forward-filled. They are recorded, retried by sync, and only
marked resolved when every expected candle in the range actually exists.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from data.fetcher import timeframe_to_ms
from data.repository import CandleRepository, GapRepository

logger = logging.getLogger(__name__)

EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


@dataclass(frozen=True)
class GapRange:
    """A contiguous run of missing candles, inclusive of both endpoints."""

    start_ts: datetime
    end_ts: datetime


@dataclass(frozen=True)
class GapAuditSummary:
    """Outcome of reconciling detected gaps against persisted data_gaps rows."""

    symbol: str
    timeframe: str
    created: int
    resolved: int
    open_ranges: tuple[GapRange, ...]


def _to_ms(moment: datetime) -> int:
    """Convert a timezone-aware datetime to epoch milliseconds."""
    return int(moment.timestamp() * 1000)


def _from_ms(epoch_ms: int) -> datetime:
    """Convert epoch milliseconds back to a UTC datetime without float rounding."""
    return EPOCH + timedelta(milliseconds=epoch_ms)


def detect_gap_ranges(
    present_ts: Iterable[datetime],
    start: datetime,
    end: datetime,
    timeframe: str,
) -> list[GapRange]:
    """
    Find contiguous runs of missing candles on the timeframe grid in [start, end].

    The expected grid is start, start + one timeframe, ... up to end (inclusive). Any
    grid point with no stored candle is missing; adjacent missing points are merged
    into a single range. start and end are assumed aligned to the timeframe boundary.

    Args:
        present_ts: Stored candle timestamps (any order).
        start: Inclusive range start, aligned to the timeframe.
        end: Inclusive range end, aligned to the timeframe.
        timeframe: Candle resolution, e.g. 1m.

    Returns:
        Missing ranges in ascending order; empty when the series is complete.
    """
    step_ms = timeframe_to_ms(timeframe)
    present_ms = {_to_ms(moment) for moment in present_ts}

    ranges: list[GapRange] = []
    run_start_ms: int | None = None
    run_end_ms: int | None = None

    grid_ms = _to_ms(start)
    end_ms = _to_ms(end)
    while grid_ms <= end_ms:
        if grid_ms not in present_ms:
            if run_start_ms is None:
                run_start_ms = grid_ms
            run_end_ms = grid_ms
        elif run_start_ms is not None:
            ranges.append(GapRange(_from_ms(run_start_ms), _from_ms(run_end_ms)))
            run_start_ms = None
        grid_ms += step_ms

    if run_start_ms is not None:
        ranges.append(GapRange(_from_ms(run_start_ms), _from_ms(run_end_ms)))
    return ranges


def find_gaps(
    symbol: str,
    timeframe: str,
    start: datetime,
    end: datetime,
    candle_repo: CandleRepository | None = None,
) -> list[GapRange]:
    """
    Detect missing candle ranges for a symbol/timeframe over an inclusive range.

    Args:
        symbol: Trading pair identifier.
        timeframe: Candle resolution, e.g. 1m.
        start: Inclusive range start, aligned to the timeframe.
        end: Inclusive range end, aligned to the timeframe.
        candle_repo: Repository to read stored timestamps. Defaults to a new instance.

    Returns:
        Missing ranges in ascending order; empty when the series is complete.
    """
    candle_repo = candle_repo or CandleRepository()
    present_ts = candle_repo.find_timestamps(symbol, timeframe, start.isoformat(), end.isoformat())
    return detect_gap_ranges(present_ts, start, end, timeframe)


def _ranges_overlap(
    a_start: datetime,
    a_end: datetime,
    b_start: datetime,
    b_end: datetime,
) -> bool:
    """Return True when two inclusive ranges share at least one point."""
    return a_start <= b_end and b_start <= a_end


def reconcile_gaps(
    symbol: str,
    timeframe: str,
    start: datetime,
    end: datetime,
    candle_repo: CandleRepository | None = None,
    gap_repo: GapRepository | None = None,
) -> GapAuditSummary:
    """
    Detect gaps in a range, persist newly found ones, and resolve filled ones.

    Newly detected ranges not already recorded as open are inserted. Open gaps that
    fall entirely inside the audited window and no longer overlap any detected gap are
    marked resolved. Gaps outside the audited window are left untouched.

    Args:
        symbol: Trading pair identifier.
        timeframe: Candle resolution, e.g. 1m.
        start: Inclusive range start, aligned to the timeframe.
        end: Inclusive range end, aligned to the timeframe.
        candle_repo: Repository for stored timestamps. Defaults to a new instance.
        gap_repo: Repository for data_gaps rows. Defaults to a new instance.

    Returns:
        Summary of how many gaps were created, resolved, and still open.

    Side effects:
        Inserts and updates rows in data_gaps.
    """
    candle_repo = candle_repo or CandleRepository()
    gap_repo = gap_repo or GapRepository()

    detected = find_gaps(symbol, timeframe, start, end, candle_repo=candle_repo)
    open_gaps = gap_repo.find_open_gaps(symbol, timeframe)
    open_bounds = {(gap.start_ts, gap.end_ts) for gap in open_gaps}

    created = 0
    for gap_range in detected:
        if (gap_range.start_ts, gap_range.end_ts) in open_bounds:
            continue
        gap_repo.create_gap(symbol, timeframe, gap_range.start_ts, gap_range.end_ts)
        created += 1

    resolved = 0
    for gap in open_gaps:
        # Only judge gaps fully inside the audited window; others were not re-checked.
        if gap.start_ts < start or gap.end_ts > end:
            continue
        still_missing = any(
            _ranges_overlap(gap.start_ts, gap.end_ts, gap_range.start_ts, gap_range.end_ts)
            for gap_range in detected
        )
        if not still_missing:
            gap_repo.mark_gap_resolved(gap.id)
            resolved += 1

    if created or resolved:
        logger.info(
            "Gap audit %s %s: %s created, %s resolved, %s still open",
            symbol,
            timeframe,
            created,
            resolved,
            len(detected),
        )
    return GapAuditSummary(symbol, timeframe, created, resolved, tuple(detected))
