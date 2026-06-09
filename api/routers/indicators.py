"""
Indicator catalog and compute endpoints.
"""

from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends

from api.deps import get_db
from api.schemas.indicators import (
    IndicatorCatalogEntry,
    IndicatorComputeRequest,
    IndicatorComputeResponse,
)
from api.services.indicator_service import IndicatorService

router = APIRouter(prefix="/indicators", tags=["indicators"])
_service = IndicatorService()


@router.get("", response_model=list[IndicatorCatalogEntry])
def list_indicators() -> list[IndicatorCatalogEntry]:
    """Return indicator registry catalog."""
    return _service.list_catalog()


@router.post("/compute", response_model=IndicatorComputeResponse)
def compute_indicators(
    body: IndicatorComputeRequest,
    conn: psycopg.Connection = Depends(get_db),
) -> IndicatorComputeResponse:
    """Batch-compute indicators for a historical window."""
    return _service.compute(
        conn,
        body.symbol,
        body.timeframe,
        body.from_,
        body.to,
        body.indicators,
    )
