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
from data.repository.candle_repository import CandleRepository


def _unix_to_iso(ts: int) -> str:
    """Convert unix seconds to an ISO timestamp string for get_candles."""
    return datetime.fromtimestamp(ts, tz=UTC).isoformat()


def _ts_to_unix(ts: pd.Timestamp) -> int:
    """Convert pandas timestamp to unix seconds."""
    return int(ts.timestamp())


class CandleService:
    """Load and paginate historical OHLCV for chart clients."""

    def __init__(
        self,
        symbol_service: SymbolService | None = None,
        candle_repository: CandleRepository | None = None,
    ) -> None:
        self._symbol_service = symbol_service or SymbolService()
        self._candle_repository = candle_repository or CandleRepository()

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

    def get_latest_candles(
        self,
        conn: psycopg.Connection,
        symbol: str,
        timeframe: str,
        limit: int | None = None,
    ) -> CandlesResponse:
        """
        Load the most recent ``limit`` bars when the requested window has no data.

        Used by chart-data when ``from``..``to`` does not overlap stored history
        (e.g. client anchors on wall-clock now but DB lags).
        """
        self._symbol_service.require_active_symbol(conn, symbol)
        validate_timeframe(timeframe)

        effective_limit = limit if limit is not None else settings.candle_default_limit()
        latest = self._candle_repository.latest_timestamp(symbol, timeframe, conn=conn)
        if latest is None:
            return CandlesResponse(symbol=symbol, timeframe=timeframe, bars=[])

        latest_unix = int(latest.timestamp())
        start = shift_unix_by_bars(latest_unix, timeframe, effective_limit - 1)
        return self.get_candles(
            conn,
            symbol,
            timeframe,
            start,
            latest_unix,
            limit=effective_limit,
        )

    def get_data_range(
        self,
        conn: psycopg.Connection,
        symbol: str,
        timeframe: str,
    ) -> tuple[int | None, int | None, int]:
        """
        Return earliest/latest unix seconds and total bar count for a series.

        Returns:
            Tuple of (earliest_unix, latest_unix, bar_count). Timestamps are
            None when no rows exist.
        """
        self._symbol_service.require_active_symbol(conn, symbol)
        validate_timeframe(timeframe)

        earliest_dt = self._candle_repository.earliest_timestamp(
            symbol, timeframe, conn=conn
        )
        latest_dt = self._candle_repository.latest_timestamp(
            symbol, timeframe, conn=conn
        )
        count = self._candle_repository.bar_count(symbol, timeframe, conn=conn)

        earliest = int(earliest_dt.timestamp()) if earliest_dt else None
        latest = int(latest_dt.timestamp()) if latest_dt else None
        return earliest, latest, count

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
