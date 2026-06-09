"""
Download OHLCV candles from an exchange via ccxt.

Provides the initial bulk fetch (fetch_ohlcv) and the incremental fetch used by sync
(fetch_since), plus a Binance -> Bybit -> OKX fallback. Closed-candle filtering keeps
the still-forming current candle out of stored data (OQ-04).

Side effect: network calls to the configured exchange API.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import ccxt
import pandas as pd

logger = logging.getLogger(__name__)

CCXT_BATCH_LIMIT = 1000
DAYS_PER_YEAR = 365
FETCH_PROGRESS_EVERY_BATCHES = 250

OHLCV_COLUMNS = ["ts", "open", "high", "low", "close", "volume"]

# Milliseconds per supported timeframe. 1m is the only canonical stored timeframe in
# Phase 1; the rest support closed-candle math for derived reads later.
TIMEFRAME_MS = {
    "1m": 60_000,
    "3m": 180_000,
    "5m": 300_000,
    "15m": 900_000,
    "30m": 1_800_000,
    "1h": 3_600_000,
    "2h": 7_200_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
    "1w": 604_800_000,
    "1M": 2_592_000_000,
}


def timeframe_to_ms(timeframe: str) -> int:
    """
    Return the duration of one candle of the given timeframe in milliseconds.

    Args:
        timeframe: Candle resolution, e.g. 1m.

    Returns:
        Duration in milliseconds.

    Raises:
        ValueError: If the timeframe is not supported.
    """
    if timeframe not in TIMEFRAME_MS:
        raise ValueError(f"Unsupported timeframe: {timeframe}. Known: {sorted(TIMEFRAME_MS)}")
    return TIMEFRAME_MS[timeframe]


def _build_exchange(exchange_id: str) -> ccxt.Exchange:
    """
    Construct a rate-limited ccxt exchange client.

    Args:
        exchange_id: ccxt exchange id, e.g. binance.

    Returns:
        A configured ccxt exchange instance.
    """
    exchange_class = getattr(ccxt, exchange_id)
    # Rate limiting avoids exchange bans during multi-page pagination.
    return exchange_class({"enableRateLimit": True})


def _paginate(
    exchange: ccxt.Exchange,
    symbol: str,
    timeframe: str,
    since_ms: int,
    until_ms: int | None = None,
) -> list[list[float | int]]:
    """
    Page through fetch_ohlcv from since_ms until the exchange stops returning new rows.

    Args:
        exchange: A ccxt exchange client.
        symbol: Trading pair, e.g. BTC/USDT.
        timeframe: Candle resolution.
        since_ms: Start timestamp in epoch milliseconds.
        until_ms: Optional inclusive upper bound; pagination stops once reached so a
            bounded range (e.g. a gap re-fetch) does not walk forward to today.

    Returns:
        Raw OHLCV rows (possibly with boundary duplicates) in fetch order.
    """
    all_rows: list[list[float | int]] = []
    batch_count = 0
    initial_since_ms = since_ms
    while True:
        batch = exchange.fetch_ohlcv(symbol, timeframe, since=since_ms, limit=CCXT_BATCH_LIMIT)
        if not batch:
            break
        batch_count += 1
        all_rows.extend(batch)
        last_ts = batch[-1][0]
        if (
            batch_count == 1
            or batch_count % FETCH_PROGRESS_EVERY_BATCHES == 0
            or len(batch) < CCXT_BATCH_LIMIT
        ):
            logger.info(
                "Fetch progress %s %s: batches=%s rows=%s last_ts=%s",
                symbol,
                timeframe,
                batch_count,
                len(all_rows),
                datetime.fromtimestamp(last_ts / 1000, tz=UTC).isoformat(),
            )
        if until_ms is not None and last_ts >= until_ms:
            break
        # +1 ms so the next request does not return the same last candle again.
        next_since = last_ts + 1
        if next_since <= since_ms:
            # Exchange returned no forward progress — stop to avoid an infinite loop.
            break
        since_ms = next_since
        if len(batch) < CCXT_BATCH_LIMIT:
            break
    logger.info(
        "Fetch complete %s %s: rows=%s batches=%s start=%s",
        symbol,
        timeframe,
        len(all_rows),
        batch_count,
        datetime.fromtimestamp(initial_since_ms / 1000, tz=UTC).isoformat(),
    )
    return all_rows


def _rows_to_frame(rows: list[list[float | int]]) -> pd.DataFrame:
    """
    Convert raw ccxt OHLCV rows into a deduplicated, sorted DataFrame.

    Args:
        rows: Raw rows from _paginate.

    Returns:
        DataFrame with columns ts, open, high, low, close, volume (UTC), empty if no rows.
    """
    if not rows:
        return pd.DataFrame(columns=OHLCV_COLUMNS)
    candles = pd.DataFrame(rows, columns=OHLCV_COLUMNS)
    candles["ts"] = pd.to_datetime(candles["ts"], unit="ms", utc=True)
    # Pagination overlap at batch boundaries can duplicate timestamps.
    return candles.drop_duplicates(subset=["ts"]).sort_values("ts").reset_index(drop=True)


def _drop_in_progress_candle(
    candles: pd.DataFrame,
    timeframe: str,
    now_ms: int | None = None,
) -> pd.DataFrame:
    """
    Remove the still-forming current candle so only closed candles are stored.

    A candle opening at T closes at T + one timeframe; it is in progress until
    now >= T + timeframe. Storing it would persist values that keep changing (OQ-04).

    Args:
        candles: Candles sorted ascending by ts.
        timeframe: Candle resolution.
        now_ms: Current time in epoch milliseconds. Defaults to wall-clock UTC now.

    Returns:
        Candles with any in-progress trailing candle removed.
    """
    if candles.empty:
        return candles
    if now_ms is None:
        now_ms = int(datetime.now(UTC).timestamp() * 1000)
    cutoff = pd.to_datetime(now_ms - timeframe_to_ms(timeframe), unit="ms", utc=True)
    return candles[candles["ts"] <= cutoff].reset_index(drop=True)


def fetch_ohlcv(
    symbol: str,
    timeframe: str,
    years: int,
    exchange_id: str,
) -> pd.DataFrame:
    """
    Fetch historical OHLCV from the exchange for a fixed number of years back.

    Args:
        symbol: Trading pair, e.g. BTC/USDT.
        timeframe: Candle resolution, e.g. 1d.
        years: How many years of history to request from today.
        exchange_id: ccxt exchange id, e.g. binance.

    Returns:
        DataFrame with columns: ts, open, high, low, close, volume (UTC).

    Raises:
        ValueError: If years is less than 1.
        ccxt.BaseError: On exchange or network failures.
    """
    if years < 1:
        raise ValueError(f"years must be >= 1, got {years}")

    exchange = _build_exchange(exchange_id)
    since_ms = int((datetime.now(UTC) - timedelta(days=DAYS_PER_YEAR * years)).timestamp() * 1000)
    rows = _paginate(exchange, symbol, timeframe, since_ms)
    return _rows_to_frame(rows)


def fetch_since(
    symbol: str,
    since_ms: int,
    exchange_id: str,
    timeframe: str = "1m",
    now_ms: int | None = None,
    until_ms: int | None = None,
) -> pd.DataFrame:
    """
    Fetch closed OHLCV candles from a starting timestamp (incremental sync path).

    The in-progress current candle is dropped so only closed candles are returned.

    Args:
        symbol: Trading pair, e.g. BTC/USDT.
        since_ms: Start timestamp in epoch milliseconds (inclusive).
        exchange_id: ccxt exchange id, e.g. binance.
        timeframe: Candle resolution. Defaults to 1m (the canonical stored resolution).
        now_ms: Current time in epoch milliseconds, for deterministic tests.
        until_ms: Optional inclusive upper bound, used to fetch a bounded range such as
            a gap re-fetch rather than everything up to now.

    Returns:
        DataFrame of closed candles with columns ts, open, high, low, close, volume (UTC).

    Raises:
        ValueError: If since_ms is negative.
        ccxt.BaseError: On exchange or network failures.
    """
    if since_ms < 0:
        raise ValueError(f"since_ms must be >= 0, got {since_ms}")

    exchange = _build_exchange(exchange_id)
    rows = _paginate(exchange, symbol, timeframe, since_ms, until_ms)
    candles = _rows_to_frame(rows)
    candles = _drop_in_progress_candle(candles, timeframe, now_ms)
    if until_ms is not None and not candles.empty:
        upper = pd.to_datetime(until_ms, unit="ms", utc=True)
        candles = candles[candles["ts"] <= upper].reset_index(drop=True)
    return candles


def fetch_since_with_fallback(
    symbol: str,
    since_ms: int,
    exchange_ids: tuple[str, ...],
    timeframe: str = "1m",
    now_ms: int | None = None,
    until_ms: int | None = None,
) -> pd.DataFrame:
    """
    Fetch closed candles, trying each exchange in order until one succeeds.

    Implements the Binance -> Bybit -> OKX fallback: a failing exchange is logged and
    the next is tried. Only when every exchange fails does the last error propagate.

    Args:
        symbol: Trading pair, e.g. BTC/USDT.
        since_ms: Start timestamp in epoch milliseconds (inclusive).
        exchange_ids: Exchanges to try, primary first.
        timeframe: Candle resolution. Defaults to 1m.
        now_ms: Current time in epoch milliseconds, for deterministic tests.
        until_ms: Optional inclusive upper bound for a bounded range fetch.

    Returns:
        DataFrame of closed candles from the first exchange that succeeds.

    Raises:
        ValueError: If exchange_ids is empty.
        ccxt.BaseError: If every exchange fails; the last error is re-raised.
    """
    if not exchange_ids:
        raise ValueError("exchange_ids must contain at least one exchange")

    last_error: ccxt.BaseError | None = None
    for exchange_id in exchange_ids:
        try:
            candles = fetch_since(
                symbol, since_ms, exchange_id, timeframe, now_ms=now_ms, until_ms=until_ms
            )
            logger.info(
                "Fetched %s closed %s candle(s) for %s from %s",
                len(candles),
                timeframe,
                symbol,
                exchange_id,
            )
            return candles
        except ccxt.BaseError as error:
            logger.warning(
                "Fetch failed for %s on %s (%s); trying next exchange",
                symbol,
                exchange_id,
                error,
            )
            last_error = error

    # Every exchange failed — surface the last error rather than returning empty data.
    raise last_error
