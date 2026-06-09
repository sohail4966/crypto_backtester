"""
Meta endpoints — health and timeframes.
"""

from __future__ import annotations

from fastapi import APIRouter

from api.schemas.meta import HealthResponse, TimeframesResponse
from api.services.timeframes import SUPPORTED_TIMEFRAMES
from data.db import connect

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Return API and database health."""
    db_status = "ok"
    try:
        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception:
        db_status = "error"
    return HealthResponse(status="ok", version="0.4.0", database=db_status)


@router.get("/timeframes", response_model=TimeframesResponse)
def timeframes() -> TimeframesResponse:
    """Return supported candle timeframes."""
    return TimeframesResponse(timeframes=SUPPORTED_TIMEFRAMES)
