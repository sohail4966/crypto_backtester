"""
Unified chart data endpoint (Phase 4b).
"""

from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends, Query

from api.deps import get_db
from api.schemas.chart_data import ChartDataResponse
from api.services.chart_data_service import ChartDataService, parse_indicator_specs

router = APIRouter(prefix="/chart-data", tags=["chart-data"])
_service = ChartDataService()


@router.get("", response_model=ChartDataResponse, response_model_by_alias=True)
def get_chart_data(
    symbol_id: str = Query(alias="symbolId"),
    timeframe: str = Query(),
    start: int = Query(),
    end: int = Query(),
    indicators: str | None = Query(default=None),
    include_signals: bool = Query(default=False, alias="includeSignals"),
    include_trades: bool = Query(default=False, alias="includeTrades"),
    limit: int | None = Query(default=None),
    conn: psycopg.Connection = Depends(get_db),
) -> ChartDataResponse:
    """Return candles and indicators for one chart window."""
    specs = parse_indicator_specs(indicators)
    return _service.get_chart_data(
        conn,
        symbol_id=symbol_id,
        timeframe=timeframe,
        start=start,
        end=end,
        indicator_specs=specs,
        include_signals=include_signals,
        include_trades=include_trades,
        limit=limit,
    )
