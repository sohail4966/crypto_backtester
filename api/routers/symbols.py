"""
Symbol catalog endpoints.
"""

from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends, Query

from api.deps import get_db
from api.schemas.symbols import SymbolResponse
from api.services.symbol_service import SymbolService

router = APIRouter(prefix="/symbols", tags=["symbols"])
_service = SymbolService()


@router.get("", response_model=list[SymbolResponse])
def list_symbols(
    q: str | None = Query(default=None),
    active_only: bool = Query(default=True),
    conn: psycopg.Connection = Depends(get_db),
) -> list[SymbolResponse]:
    """List tradable symbols from app.symbols."""
    return _service.list_symbols(conn, query=q, active_only=active_only)


@router.get("/{symbol:path}", response_model=SymbolResponse)
def get_symbol(
    symbol: str,
    conn: psycopg.Connection = Depends(get_db),
) -> SymbolResponse:
    """Return metadata for one symbol."""
    return _service.get_symbol(conn, symbol)
