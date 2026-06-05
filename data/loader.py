"""
Load candles from TimescaleDB into pandas — the single downstream boundary.

Downstream modules must use get_candles() rather than querying the database directly.
Reads go through CandleRepository; SQL is defined in data.repository.queries.
"""

from __future__ import annotations

import pandas as pd

from data.repository import CandleRepository

_repository = CandleRepository()


def get_candles(
    symbol: str,
    timeframe: str,
    start: str,
    end: str,
) -> pd.DataFrame:
    """
    Load OHLCV candles for a symbol and timeframe.

    Args:
        symbol: Trading pair, e.g. BTC/USDT.
        timeframe: Candle resolution, e.g. 1d.
        start: Inclusive start date (ISO), e.g. 2024-01-01.
        end: Inclusive end date (ISO), e.g. 2024-12-31.

    Returns:
        DataFrame with columns ts, open, high, low, close, volume (UTC).
        Empty when no rows match the range.
    """
    rows, column_names = _repository.find_by_date_range(symbol, timeframe, start, end)
    candles = pd.DataFrame(rows, columns=column_names)
    if candles.empty:
        return candles
    # Enforce UTC so indicator and backtest code never mix naive timestamps.
    candles["ts"] = pd.to_datetime(candles["ts"], utc=True)
    return candles
