"""
Download OHLCV candles from an exchange via ccxt.

Side effect: network calls to the configured exchange API.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import ccxt
import pandas as pd

CCXT_BATCH_LIMIT = 1000
DAYS_PER_YEAR = 365


def fetch_ohlcv(
    symbol: str,
    timeframe: str,
    years: int,
    exchange_id: str,
) -> pd.DataFrame:
    """
    Fetch historical OHLCV from the exchange.

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

    exchange_class = getattr(ccxt, exchange_id)
    # Rate limiting avoids Binance bans during multi-page pagination.
    exchange = exchange_class({"enableRateLimit": True})

    since_ms = int((datetime.now(UTC) - timedelta(days=DAYS_PER_YEAR * years)).timestamp() * 1000)
    all_rows: list[list[float | int]] = []

    while True:
        batch = exchange.fetch_ohlcv(symbol, timeframe, since=since_ms, limit=CCXT_BATCH_LIMIT)
        if not batch:
            break
        all_rows.extend(batch)
        last_ts = batch[-1][0]
        # +1 ms so the next request does not return the same last candle again.
        next_since = last_ts + 1
        if next_since <= since_ms:
            # Exchange returned no forward progress — stop to avoid an infinite loop.
            break
        since_ms = next_since
        if len(batch) < CCXT_BATCH_LIMIT:
            break

    if not all_rows:
        return pd.DataFrame(columns=["ts", "open", "high", "low", "close", "volume"])

    candles = pd.DataFrame(all_rows, columns=["ts", "open", "high", "low", "close", "volume"])
    candles["ts"] = pd.to_datetime(candles["ts"], unit="ms", utc=True)
    # Pagination overlap at batch boundaries can duplicate timestamps.
    return candles.drop_duplicates(subset=["ts"]).sort_values("ts").reset_index(drop=True)
