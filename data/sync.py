"""
Sync orchestrator: keep canonical 1m candles current for every configured symbol.

Per pass and per symbol it (1) fetches new closed candles incrementally, (2) audits a
bounded recent window for gaps, and (3) retries still-open gaps with a bounded re-fetch.
Per-symbol failures are isolated: one bad pair is logged and reported, the rest continue.
At most max_concurrent_symbols run at once, relying on ccxt's built-in rate limiting.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import ccxt

from data.config import DataConfig, SyncConfig
from data.fetcher import CCXT_BATCH_LIMIT, fetch_since_with_fallback, timeframe_to_ms
from data.gaps import reconcile_gaps
from data.repository import CandleRepository, GapRepository

logger = logging.getLogger(__name__)

MINUTE_MS = 60_000
INSERT_EVERY_BATCHES = 25

# Per-pass gap audit is scoped to this recent window so the hourly path stays cheap
# instead of rescanning the full multi-year 1m history every run.
GAP_AUDIT_LOOKBACK = timedelta(days=2)

_HISTORY_PATTERN = re.compile(r"^(\d+)([ywdh])$")


@dataclass(frozen=True)
class SyncResult:
    """Outcome of syncing one symbol in one pass."""

    symbol: str
    timeframe: str
    fetched: int
    inserted: int
    gaps_created: int
    gaps_resolved: int
    status: str
    error: str | None = None


def history_to_timedelta(history: str) -> timedelta:
    """
    Parse a history depth string such as '8y' or '30d' into a timedelta.

    Args:
        history: Depth as <amount><unit> where unit is y, w, d, or h.

    Returns:
        The corresponding timedelta (years are treated as 365 days).

    Raises:
        ValueError: If the string does not match the expected format.

    Note:
        Year conversion uses 365 days, ignoring leap years. Over 8 years this
        understates the true span by ~2 days — acceptable for an initial backfill
        start point. If calendar-exact arithmetic is ever needed, replace with
        dateutil.relativedelta and pass the reference datetime explicitly.
    """
    match = _HISTORY_PATTERN.match(history.strip())
    if not match:
        raise ValueError(f"Unsupported history format: {history!r}. Expected e.g. 8y, 30d, 12h")
    amount, unit = int(match.group(1)), match.group(2)
    if unit == "y":
        return timedelta(days=365 * amount)
    if unit == "w":
        return timedelta(weeks=amount)
    if unit == "d":
        return timedelta(days=amount)
    return timedelta(hours=amount)


def _to_ms(moment: datetime) -> int:
    """Convert a timezone-aware datetime to epoch milliseconds."""
    return int(moment.timestamp() * 1000)


def _chunk_end_ms(start_ms: int, timeframe: str) -> int:
    """
    Return an inclusive chunk end for INSERT_EVERY_BATCHES * CCXT_BATCH_LIMIT candles.

    Args:
        start_ms: Inclusive starting candle timestamp in epoch milliseconds.
        timeframe: Candle resolution string.

    Returns:
        Inclusive chunk end timestamp in epoch milliseconds.
    """
    step_ms = timeframe_to_ms(timeframe)
    candles_per_chunk = INSERT_EVERY_BATCHES * CCXT_BATCH_LIMIT
    return start_ms + (candles_per_chunk - 1) * step_ms


def _since_ms_for_symbol(latest: datetime | None, history: str, now_ms: int) -> int:
    """
    Decide the fetch start: full history on first sync, else one minute before latest.

    Args:
        latest: Most recent stored candle timestamp, or None when empty.
        history: Configured initial history depth (e.g. 8y).
        now_ms: Current time in epoch milliseconds.

    Returns:
        Epoch milliseconds to start fetching from.
    """
    if latest is None:
        return now_ms - int(history_to_timedelta(history).total_seconds() * 1000)
    # Overlap one minute so a boundary candle is never skipped; duplicates are ignored.
    return _to_ms(latest) - MINUTE_MS


def _audit_recent_window(
    symbol: str,
    timeframe: str,
    candle_repo: CandleRepository,
    gap_repo: GapRepository,
) -> tuple[int, int]:
    """
    Reconcile gaps over the recent lookback window after a fetch.

    Args:
        symbol: Trading pair identifier.
        timeframe: Candle resolution string.
        candle_repo: Candle repository.
        gap_repo: Gap repository.

    Returns:
        Tuple of (gaps_created, gaps_resolved) within the window.
    """
    audit_end = candle_repo.latest_timestamp(symbol, timeframe)
    if audit_end is None:
        return 0, 0
    # audit_end is a stored candle (grid-aligned); subtracting whole days stays aligned.
    # TODO: A symbol with less than GAP_AUDIT_LOOKBACK of history would flag pre-listing
    #       minutes as gaps. All Phase 1 symbols exceed this window; revisit for new listings.
    audit_start = audit_end - GAP_AUDIT_LOOKBACK
    summary = reconcile_gaps(symbol, timeframe, audit_start, audit_end, candle_repo, gap_repo)
    return summary.created, summary.resolved


def _retry_open_gaps(
    symbol: str,
    timeframe: str,
    exchanges: tuple[str, ...],
    candle_repo: CandleRepository,
    gap_repo: GapRepository,
    now_ms: int,
) -> int:
    """
    Re-fetch each still-open gap's bounded range and resolve it if now filled.

    Args:
        symbol: Trading pair identifier.
        timeframe: Candle resolution string.
        exchanges: Exchanges to try, primary first.
        candle_repo: Candle repository.
        gap_repo: Gap repository.
        now_ms: Current time in epoch milliseconds.

    Returns:
        Number of gaps resolved by the retries.

    Side effects:
        Fetches from exchanges and writes candles and gap bookkeeping.
    """
    resolved = 0
    open_gaps = gap_repo.find_open_gaps(symbol, timeframe)
    if open_gaps:
        logger.info("Retrying %s open gap(s) for %s %s", len(open_gaps), symbol, timeframe)
    for gap in open_gaps:
        try:
            gap_candles = fetch_since_with_fallback(
                symbol,
                _to_ms(gap.start_ts),
                exchanges,
                timeframe,
                now_ms=now_ms,
                until_ms=_to_ms(gap.end_ts),
            )
            if not gap_candles.empty:
                candle_repo.insert_new_candles(symbol, timeframe, gap_candles)
            gap_repo.record_gap_retry(gap.id)
        except ccxt.BaseError as error:
            logger.warning("Gap retry failed %s %s gap_id=%s: %s", symbol, timeframe, gap.id, error)
            gap_repo.record_gap_retry(gap.id, last_error=str(error))
            continue
        summary = reconcile_gaps(symbol, timeframe, gap.start_ts, gap.end_ts, candle_repo, gap_repo)
        resolved += summary.resolved
    return resolved


def sync_symbol(
    symbol: str,
    history: str,
    exchanges: tuple[str, ...],
    sync_config: SyncConfig,
    timeframe: str = "1m",
    candle_repo: CandleRepository | None = None,
    gap_repo: GapRepository | None = None,
    now_ms: int | None = None,
) -> SyncResult:
    """
    Sync one symbol: incremental fetch, gap audit, and gap retries.

    Any failure for this symbol is caught and returned as a failed SyncResult so a single
    bad pair never aborts the whole run.

    Args:
        symbol: Trading pair identifier.
        history: Configured initial history depth (e.g. 8y).
        exchanges: Exchanges to try, primary first.
        sync_config: Sync policy settings.
        timeframe: Canonical stored resolution. Defaults to 1m.
        candle_repo: Candle repository. Defaults to a new instance.
        gap_repo: Gap repository. Defaults to a new instance.
        now_ms: Current time in epoch milliseconds, for deterministic tests.

    Returns:
        A SyncResult describing fetched/inserted counts, gap activity, and status.

    Side effects:
        Network fetches and database writes.
    """
    candle_repo = candle_repo or CandleRepository()
    gap_repo = gap_repo or GapRepository()
    if now_ms is None:
        now_ms = int(datetime.now(UTC).timestamp() * 1000)

    try:
        latest = candle_repo.latest_timestamp(symbol, timeframe)
        since_ms = _since_ms_for_symbol(latest, history, now_ms)
        step_ms = timeframe_to_ms(timeframe)
        closed_until_ms = now_ms - step_ms
        logger.info(
            "Starting sync %s %s: latest_ts=%s since=%s",
            symbol,
            timeframe,
            latest.isoformat() if latest else "none",
            datetime.fromtimestamp(since_ms / 1000, tz=UTC).isoformat(),
        )
        fetched = 0
        inserted = 0
        chunk_index = 0
        chunk_start_ms = since_ms
        while chunk_start_ms <= closed_until_ms:
            chunk_index += 1
            chunk_end_ms = min(_chunk_end_ms(chunk_start_ms, timeframe), closed_until_ms)
            candles = fetch_since_with_fallback(
                symbol,
                chunk_start_ms,
                exchanges,
                timeframe,
                now_ms=now_ms,
                until_ms=chunk_end_ms,
            )
            chunk_fetched = len(candles)
            chunk_inserted = (
                candle_repo.insert_new_candles(symbol, timeframe, candles) if chunk_fetched else 0
            )
            fetched += chunk_fetched
            inserted += chunk_inserted
            logger.info(
                "Chunk stored %s %s: chunk=%s fetched=%s inserted=%s range=%s..%s",
                symbol,
                timeframe,
                chunk_index,
                chunk_fetched,
                chunk_inserted,
                datetime.fromtimestamp(chunk_start_ms / 1000, tz=UTC).isoformat(),
                datetime.fromtimestamp(chunk_end_ms / 1000, tz=UTC).isoformat(),
            )
            chunk_start_ms = chunk_end_ms + step_ms
        logger.info(
            "Stored %s %s: fetched=%s inserted=%s duplicates_or_existing=%s",
            symbol,
            timeframe,
            fetched,
            inserted,
            max(fetched - inserted, 0),
        )

        created, resolved = _audit_recent_window(symbol, timeframe, candle_repo, gap_repo)
        if sync_config.retry_gaps:
            resolved += _retry_open_gaps(
                symbol, timeframe, exchanges, candle_repo, gap_repo, now_ms
            )

        logger.info(
            "Synced %s %s: fetched=%s inserted=%s gaps +%s/-%s",
            symbol,
            timeframe,
            fetched,
            inserted,
            created,
            resolved,
        )
        return SyncResult(symbol, timeframe, fetched, inserted, created, resolved, "ok")
    except Exception as error:
        # Fault isolation: record and report this pair's failure, let the others run.
        logger.exception("Sync failed for %s %s", symbol, timeframe)
        return SyncResult(symbol, timeframe, 0, 0, 0, 0, "failed", str(error))


def sync_all(
    config: DataConfig,
    candle_repo: CandleRepository | None = None,
    gap_repo: GapRepository | None = None,
    progress_callback: Callable[[int, int, SyncResult], None] | None = None,
) -> list[SyncResult]:
    """
    Sync every configured symbol, at most max_concurrent_symbols at a time.

    Args:
        config: Parsed data ingestion configuration.
        candle_repo: Candle repository shared across workers. Defaults to a new instance.
        gap_repo: Gap repository shared across workers. Defaults to a new instance.
        progress_callback: Optional callback invoked as each symbol finishes with
            (completed_count, total_symbols, result).

    Returns:
        One SyncResult per configured symbol (order not guaranteed).

    Side effects:
        Network fetches and database writes for all symbols.
    """
    max_workers = max(1, config.sync.max_concurrent_symbols)
    results: list[SyncResult] = []
    total_symbols = len(config.symbols)
    completed = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                sync_symbol,
                symbol.symbol,
                symbol.history,
                config.exchanges.ordered,
                config.sync,
                config.timeframe,
                candle_repo,
                gap_repo,
            )
            for symbol in config.symbols
        ]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            completed += 1
            if progress_callback is not None:
                progress_callback(completed, total_symbols, result)
    return results
