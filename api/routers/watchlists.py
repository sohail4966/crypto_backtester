"""
Watchlist endpoints scoped by user_id.
"""

from __future__ import annotations

from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends

from api.deps import get_db
from api.schemas.watchlists import (
    WatchlistCreate,
    WatchlistResponse,
    WatchlistSymbolsUpdate,
    WatchlistUpdate,
)
from api.services.watchlist_service import WatchlistService

router = APIRouter(tags=["watchlists"])
_service = WatchlistService()


@router.get("/users/{user_id}/watchlists", response_model=list[WatchlistResponse])
def list_watchlists(
    user_id: UUID,
    conn: psycopg.Connection = Depends(get_db),
) -> list[WatchlistResponse]:
    """List watchlists for a user."""
    return _service.list_watchlists(conn, user_id)


@router.post("/users/{user_id}/watchlists", response_model=WatchlistResponse, status_code=201)
def create_watchlist(
    user_id: UUID,
    body: WatchlistCreate,
    conn: psycopg.Connection = Depends(get_db),
) -> WatchlistResponse:
    """Create a watchlist."""
    return _service.create_watchlist(conn, user_id, body)


@router.get("/users/{user_id}/watchlists/{watchlist_id}", response_model=WatchlistResponse)
def get_watchlist(
    user_id: UUID,
    watchlist_id: UUID,
    conn: psycopg.Connection = Depends(get_db),
) -> WatchlistResponse:
    """Fetch one watchlist."""
    return _service.get_watchlist(conn, user_id, watchlist_id)


@router.patch("/users/{user_id}/watchlists/{watchlist_id}", response_model=WatchlistResponse)
def update_watchlist(
    user_id: UUID,
    watchlist_id: UUID,
    body: WatchlistUpdate,
    conn: psycopg.Connection = Depends(get_db),
) -> WatchlistResponse:
    """Update watchlist metadata."""
    return _service.update_watchlist(conn, user_id, watchlist_id, body)


@router.delete("/users/{user_id}/watchlists/{watchlist_id}", status_code=204)
def delete_watchlist(
    user_id: UUID,
    watchlist_id: UUID,
    conn: psycopg.Connection = Depends(get_db),
) -> None:
    """Delete a watchlist."""
    _service.delete_watchlist(conn, user_id, watchlist_id)


@router.put("/users/{user_id}/watchlists/{watchlist_id}/symbols", response_model=WatchlistResponse)
def replace_watchlist_symbols(
    user_id: UUID,
    watchlist_id: UUID,
    body: WatchlistSymbolsUpdate,
    conn: psycopg.Connection = Depends(get_db),
) -> WatchlistResponse:
    """Replace ordered symbols in a watchlist."""
    return _service.replace_symbols(conn, user_id, watchlist_id, body)
