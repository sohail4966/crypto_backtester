"""
Historical candle endpoints.
"""

from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends, Query

from api.deps import get_db
from api.schemas.candles import CandlesResponse
from api.services.candle_service import CandleService

router = APIRouter(prefix="/candles", tags=["candles"])
_service = CandleService()


@router.get("/{symbol:path}", response_model=CandlesResponse)
def get_candles(
    symbol: str,
    timeframe: str = Query(...),
    from_: int = Query(..., alias="from"),
    to: int = Query(...),
    limit: int | None = Query(default=None),
    conn: psycopg.Connection = Depends(get_db),
) -> CandlesResponse:
    """Load paginated historical OHLCV."""
    return _service.get_candles(conn, symbol, timeframe, from_, to, limit=limit)
