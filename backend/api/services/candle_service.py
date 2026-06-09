"""
Historical candle loading and chart formatting.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
import psycopg

from api import settings
from api.exceptions import ValidationError
from api.schemas.candles import Bar, CandlesResponse
from api.services.symbol_service import SymbolService
from api.services.timeframes import shift_unix_by_bars, validate_timeframe
from data.loader import get_candles


def _unix_to_iso(ts: int) -> str:
    """Convert unix seconds to an ISO timestamp string for get_candles."""
    return datetime.fromtimestamp(ts, tz=UTC).isoformat()


def _ts_to_unix(ts: pd.Timestamp) -> int:
    """Convert pandas timestamp to unix seconds."""
    return int(ts.timestamp())


class CandleService:
    """Load and paginate historical OHLCV for chart clients."""

    def __init__(self, symbol_service: SymbolService | None = None) -> None:
        self._symbol_service = symbol_service or SymbolService()

    def get_candles(
        self,
        conn: psycopg.Connection,
        symbol: str,
        timeframe: str,
        from_ts: int,
        to_ts: int,
        limit: int | None = None,
    ) -> CandlesResponse:
        """
        Load historical candles with optional pagination cursor.

        Args:
            conn: Database connection for symbol validation.
            symbol: Trading pair.
            timeframe: Candle resolution.
            from_ts: Inclusive start unix seconds.
            to_ts: Inclusive end unix seconds.
            limit: Max bars; defaults to settings default.

        Returns:
            Chart-formatted candle response.
        """
        self._symbol_service.require_active_symbol(conn, symbol)
        try:
            validate_timeframe(timeframe)
        except ValueError as exc:
            raise ValidationError("INVALID_TIMEFRAME", str(exc)) from exc

        if from_ts > to_ts:
            raise ValidationError("INVALID_RANGE", "from must be <= to")

        effective_limit = limit if limit is not None else settings.candle_default_limit()
        max_limit = settings.candle_max_limit()
        if effective_limit > max_limit:
            raise ValidationError(
                "LIMIT_EXCEEDED",
                f"limit must be <= {max_limit}",
            )

        start = _unix_to_iso(from_ts)
        end = _unix_to_iso(to_ts)
        df = get_candles(symbol, timeframe, start, end)
        if df.empty:
            return CandlesResponse(symbol=symbol, timeframe=timeframe, bars=[])

        bars = [
            Bar(
                time=_ts_to_unix(row.ts),
                open=float(row.open),
                high=float(row.high),
                low=float(row.low),
                close=float(row.close),
                volume=float(row.volume),
            )
            for row in df.itertuples(index=False)
        ]

        next_from: int | None = None
        if len(bars) > effective_limit:
            truncated = bars[:effective_limit]
            next_from = truncated[-1].time + 1
            bars = truncated

        return CandlesResponse(
            symbol=symbol,
            timeframe=timeframe,
            bars=bars,
            next_from=next_from,
        )

    def load_dataframe(
        self,
        conn: psycopg.Connection,
        symbol: str,
        timeframe: str,
        from_ts: int,
        to_ts: int,
        *,
        warmup_bars: int = 0,
    ) -> pd.DataFrame:
        """
        Load full OHLCV DataFrame for indicator/replay use.

        Args:
            conn: Database connection.
            symbol: Trading pair.
            timeframe: Candle resolution.
            from_ts: Inclusive start unix seconds.
            to_ts: Inclusive end unix seconds.
            warmup_bars: Extra bars to load before ``from_ts`` for indicator seeding.

        Returns:
            OHLCV DataFrame from get_candles.
        """
        self._symbol_service.require_active_symbol(conn, symbol)
        validate_timeframe(timeframe)
        load_from = from_ts
        if warmup_bars > 0:
            load_from = shift_unix_by_bars(from_ts, timeframe, warmup_bars)
        return get_candles(symbol, timeframe, _unix_to_iso(load_from), _unix_to_iso(to_ts))
