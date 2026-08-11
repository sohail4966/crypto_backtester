"""
Watchlist endpoints scoped by user_id (JWT ownership required).
"""

from __future__ import annotations

from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends

from api.deps import get_current_user, get_db, require_same_user
from api.repositories.user_repository import UserRow
from api.schemas.watchlists import (
    WatchlistCreate,
    WatchlistResponse,
    WatchlistSymbolsUpdate,
    WatchlistUpdate,
)
from api.services.watchlist_service import WatchlistService

router = APIRouter(tags=["watchlists"])
_service = WatchlistService()


def _authorize(user_id: UUID, current: UserRow) -> None:
    """Require JWT subject to match path user_id."""
    require_same_user(user_id, current)


@router.get("/users/{user_id}/watchlists", response_model=list[WatchlistResponse])
def list_watchlists(
    user_id: UUID,
    conn: psycopg.Connection = Depends(get_db),
    current: UserRow = Depends(get_current_user),
) -> list[WatchlistResponse]:
    """List watchlists for a user."""
    _authorize(user_id, current)
    return _service.list_watchlists(conn, user_id)


@router.post("/users/{user_id}/watchlists", response_model=WatchlistResponse, status_code=201)
def create_watchlist(
    user_id: UUID,
    body: WatchlistCreate,
    conn: psycopg.Connection = Depends(get_db),
    current: UserRow = Depends(get_current_user),
) -> WatchlistResponse:
    """Create a watchlist."""
    _authorize(user_id, current)
    return _service.create_watchlist(conn, user_id, body)


@router.get("/users/{user_id}/watchlists/{watchlist_id}", response_model=WatchlistResponse)
def get_watchlist(
    user_id: UUID,
    watchlist_id: UUID,
    conn: psycopg.Connection = Depends(get_db),
    current: UserRow = Depends(get_current_user),
) -> WatchlistResponse:
    """Fetch one watchlist."""
    _authorize(user_id, current)
    return _service.get_watchlist(conn, user_id, watchlist_id)


@router.patch("/users/{user_id}/watchlists/{watchlist_id}", response_model=WatchlistResponse)
def update_watchlist(
    user_id: UUID,
    watchlist_id: UUID,
    body: WatchlistUpdate,
    conn: psycopg.Connection = Depends(get_db),
    current: UserRow = Depends(get_current_user),
) -> WatchlistResponse:
    """Update watchlist metadata."""
    _authorize(user_id, current)
    return _service.update_watchlist(conn, user_id, watchlist_id, body)


@router.delete("/users/{user_id}/watchlists/{watchlist_id}", status_code=204)
def delete_watchlist(
    user_id: UUID,
    watchlist_id: UUID,
    conn: psycopg.Connection = Depends(get_db),
    current: UserRow = Depends(get_current_user),
) -> None:
    """Delete a watchlist."""
    _authorize(user_id, current)
    _service.delete_watchlist(conn, user_id, watchlist_id)


@router.put("/users/{user_id}/watchlists/{watchlist_id}/symbols", response_model=WatchlistResponse)
def replace_watchlist_symbols(
    user_id: UUID,
    watchlist_id: UUID,
    body: WatchlistSymbolsUpdate,
    conn: psycopg.Connection = Depends(get_db),
    current: UserRow = Depends(get_current_user),
) -> WatchlistResponse:
    """Replace ordered symbols in a watchlist."""
    _authorize(user_id, current)
    return _service.replace_symbols(conn, user_id, watchlist_id, body)
