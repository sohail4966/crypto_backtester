"""
Symbol catalog endpoints.
"""

from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends, Query

from api.deps import get_db
from api.schemas.candles import CandleDataRangeResponse
from api.schemas.symbols import SymbolResponse
from api.services.candle_service import CandleService
from api.services.symbol_service import SymbolService

router = APIRouter(prefix="/symbols", tags=["symbols"])
_service = SymbolService()
_candles = CandleService()


@router.get("", response_model=list[SymbolResponse], response_model_by_alias=True)
def list_symbols(
    q: str | None = Query(default=None),
    active_only: bool = Query(default=True),
    conn: psycopg.Connection = Depends(get_db),
) -> list[SymbolResponse]:
    """List tradable symbols from app.symbols."""
    return _service.list_symbols(conn, query=q, active_only=active_only)


@router.get("/search", response_model=list[SymbolResponse], response_model_by_alias=True)
def search_symbols(
    q: str | None = Query(default=None),
    active_only: bool = Query(default=True),
    conn: psycopg.Connection = Depends(get_db),
) -> list[SymbolResponse]:
    """Alias for symbol search (SPEC-001 path)."""
    return _service.list_symbols(conn, query=q, active_only=active_only)


@router.get(
    "/{symbol:path}/data-range",
    response_model=CandleDataRangeResponse,
    response_model_by_alias=True,
)
def get_symbol_data_range(
    symbol: str,
    timeframe: str = Query(),
    conn: psycopg.Connection = Depends(get_db),
) -> CandleDataRangeResponse:
    """Return earliest/latest stored candle timestamps for chart anchoring."""
    _service.get_symbol(conn, symbol)
    earliest, latest, bar_count = _candles.get_data_range(conn, symbol, timeframe)
    return CandleDataRangeResponse(
        symbol_id=symbol,
        timeframe=timeframe,
        earliest=earliest,
        latest=latest,
        bar_count=bar_count,
    )


@router.get("/{symbol:path}", response_model=SymbolResponse, response_model_by_alias=True)
def get_symbol(
    symbol: str,
    conn: psycopg.Connection = Depends(get_db),
) -> SymbolResponse:
    """Return metadata for one symbol."""
    return _service.get_symbol(conn, symbol)
