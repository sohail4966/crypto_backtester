"""
Unified chart data bundling for frontend clients (Phase 4b).
"""

from __future__ import annotations

import json
from typing import Any

import psycopg

from api import settings
from api.exceptions import ValidationError
from api.schemas.chart_data import ChartDataResponse, Signal, Trade
from api.schemas.indicators import IndicatorSpec
from api.services.candle_service import CandleService
from api.services.indicator_service import IndicatorService
from api.services.symbol_service import SymbolService
from api.services.timeframes import TIMEFRAME_SECONDS, validate_timeframe


def indicator_series_id(key: str, params: dict[str, Any]) -> str:
    """
    Build a stable client-facing indicator map key.

    Examples: RSI + {period: 14} -> RSI_14; MACD + multi-param -> MACD_12_26_9
    """
    indicator = key.upper()
    if not params:
        return indicator
    if len(params) == 1 and "period" in params:
        return f"{indicator}_{params['period']}"
    parts = "_".join(str(params[name]) for name in sorted(params))
    return f"{indicator}_{parts}"


def parse_indicator_specs(raw: str | None) -> list[IndicatorSpec]:
    """Parse URL-encoded JSON indicator array."""
    if not raw:
        return []
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValidationError("INVALID_INDICATOR", f"Invalid indicators JSON: {exc}") from exc
    if not isinstance(payload, list):
        raise ValidationError("INVALID_INDICATOR", "indicators must be a JSON array")
    return [IndicatorSpec.model_validate(item) for item in payload]


class ChartDataService:
    """Bundle candles and indicators into one chart window response."""

    def __init__(
        self,
        candle_service: CandleService | None = None,
        indicator_service: IndicatorService | None = None,
        symbol_service: SymbolService | None = None,
    ) -> None:
        self._candles = candle_service or CandleService()
        self._indicators = indicator_service or IndicatorService()
        self._symbols = symbol_service or SymbolService()

    def get_chart_data(
        self,
        conn: psycopg.Connection,
        *,
        symbol_id: str,
        timeframe: str,
        start: int,
        end: int,
        indicator_specs: list[IndicatorSpec],
        include_signals: bool = False,
        include_trades: bool = False,
        limit: int | None = None,
    ) -> ChartDataResponse:
        """
        Load a unified chart window for the requested symbol and range.

        Args:
            conn: Database connection.
            symbol_id: Stable symbol id (= app.symbols.symbol).
            timeframe: Candle resolution.
            start: Inclusive window start (unix seconds).
            end: Inclusive window end (unix seconds).
            indicator_specs: Indicators to compute on the window.
            include_signals: When true, include signals (empty until Phase 4c).
            include_trades: When true, include trades (empty until Phase 4c).
            limit: Max bars returned (default from settings).

        Returns:
            ChartDataResponse with aligned candles and indicator points.
        """
        _ = include_signals
        _ = include_trades

        try:
            validate_timeframe(timeframe)
        except ValueError as exc:
            raise ValidationError("INVALID_TIMEFRAME", str(exc)) from exc

        if start > end:
            raise ValidationError("INVALID_RANGE", "start must be <= end")

        effective_limit = limit if limit is not None else settings.chart_data_default_limit()
        max_limit = settings.candle_max_limit()
        if effective_limit > max_limit:
            raise ValidationError("LIMIT_EXCEEDED", f"limit must be <= {max_limit}")

        symbol = self._symbols.require_active_symbol(conn, symbol_id)
        candles_response = self._candles.get_candles(
            conn,
            symbol_id,
            timeframe,
            start,
            end,
            limit=effective_limit,
        )
        if not candles_response.bars:
            candles_response = self._candles.get_latest_candles(
                conn,
                symbol_id,
                timeframe,
                limit=effective_limit,
            )

        indicator_map: dict[str, list] = {}
        if indicator_specs and candles_response.bars:
            compute_response = self._indicators.compute(
                conn,
                symbol_id,
                timeframe,
                candles_response.bars[0].time,
                candles_response.bars[-1].time,
                indicator_specs,
            )
            for series in compute_response.series:
                series_id = indicator_series_id(series.key, series.params)
                indicator_map[series_id] = series.points

        chunk_start = candles_response.bars[0].time if candles_response.bars else start
        chunk_end = candles_response.bars[-1].time if candles_response.bars else end
        next_start = candles_response.next_from
        if next_start is None and candles_response.bars:
            bar_seconds = TIMEFRAME_SECONDS[timeframe]
            candidate = candles_response.bars[-1].time + bar_seconds
            if candidate <= end:
                next_start = candidate

        return ChartDataResponse(
            symbol=symbol,
            timeframe=timeframe,
            start=chunk_start,
            end=chunk_end,
            candles=candles_response.bars,
            indicators=indicator_map,
            signals=[],
            trades=[],
            next_start=next_start,
        )
