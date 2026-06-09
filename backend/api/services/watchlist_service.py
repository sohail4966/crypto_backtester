"""
Watchlist management service.
"""

from __future__ import annotations

from uuid import UUID

import psycopg

from api.exceptions import NotFoundError, ValidationError
from api.repositories.symbol_repository import SymbolRepository
from api.repositories.user_repository import UserRepository
from api.repositories.watchlist_repository import WatchlistRepository
from api.schemas.watchlists import (
    WatchlistCreate,
    WatchlistResponse,
    WatchlistSymbolsUpdate,
    WatchlistUpdate,
)


class WatchlistService:
    """CRUD for user watchlists."""

    def __init__(
        self,
        watchlist_repository: WatchlistRepository | None = None,
        user_repository: UserRepository | None = None,
        symbol_repository: SymbolRepository | None = None,
    ) -> None:
        self._watchlists = watchlist_repository or WatchlistRepository()
        self._users = user_repository or UserRepository()
        self._symbols = symbol_repository or SymbolRepository()

    def _ensure_user(self, conn: psycopg.Connection, user_id: UUID) -> None:
        """Raise if user does not exist."""
        if self._users.get_by_id(conn, user_id) is None:
            raise NotFoundError("USER_NOT_FOUND", f"Unknown user: {user_id}")

    def _validate_symbols(self, conn: psycopg.Connection, symbols: list[str]) -> None:
        """Ensure all symbols exist and are active."""
        for symbol in symbols:
            row = self._symbols.get_symbol(conn, symbol)
            if row is None or not row.is_active:
                raise ValidationError("INVALID_SYMBOL", f"Unknown or inactive symbol: {symbol}")

    def _to_response(self, conn: psycopg.Connection, row: object) -> WatchlistResponse:
        """Build watchlist response with symbols."""
        symbols = self._watchlists.get_symbols(conn, row.id)
        return WatchlistResponse(
            id=row.id,
            user_id=row.user_id,
            name=row.name,
            is_default=row.is_default,
            sort_order=row.sort_order,
            symbols=symbols,
            created_at=row.created_at,
        )

    def list_watchlists(self, conn: psycopg.Connection, user_id: UUID) -> list[WatchlistResponse]:
        """List all watchlists for a user."""
        self._ensure_user(conn, user_id)
        rows = self._watchlists.list_by_user(conn, user_id)
        return [self._to_response(conn, row) for row in rows]

    def create_watchlist(
        self,
        conn: psycopg.Connection,
        user_id: UUID,
        body: WatchlistCreate,
    ) -> WatchlistResponse:
        """Create watchlist with optional symbols."""
        self._ensure_user(conn, user_id)
        if body.symbols:
            self._validate_symbols(conn, body.symbols)
        row = self._watchlists.create(conn, user_id, body.name)
        if body.symbols:
            self._watchlists.set_symbols(conn, row.id, body.symbols)
        return self._to_response(conn, row)

    def get_watchlist(
        self,
        conn: psycopg.Connection,
        user_id: UUID,
        watchlist_id: UUID,
    ) -> WatchlistResponse:
        """Fetch one watchlist."""
        row = self._watchlists.get_by_id(conn, user_id, watchlist_id)
        if row is None:
            raise NotFoundError("WATCHLIST_NOT_FOUND", f"Unknown watchlist: {watchlist_id}")
        return self._to_response(conn, row)

    def update_watchlist(
        self,
        conn: psycopg.Connection,
        user_id: UUID,
        watchlist_id: UUID,
        body: WatchlistUpdate,
    ) -> WatchlistResponse:
        """Patch watchlist metadata."""
        row = self._watchlists.update(
            conn,
            user_id,
            watchlist_id,
            body.name,
            body.is_default,
            body.sort_order,
        )
        if row is None:
            raise NotFoundError("WATCHLIST_NOT_FOUND", f"Unknown watchlist: {watchlist_id}")
        return self._to_response(conn, row)

    def delete_watchlist(
        self,
        conn: psycopg.Connection,
        user_id: UUID,
        watchlist_id: UUID,
    ) -> None:
        """Delete watchlist."""
        if not self._watchlists.delete(conn, user_id, watchlist_id):
            raise NotFoundError("WATCHLIST_NOT_FOUND", f"Unknown watchlist: {watchlist_id}")

    def replace_symbols(
        self,
        conn: psycopg.Connection,
        user_id: UUID,
        watchlist_id: UUID,
        body: WatchlistSymbolsUpdate,
    ) -> WatchlistResponse:
        """Replace ordered symbols."""
        row = self._watchlists.get_by_id(conn, user_id, watchlist_id)
        if row is None:
            raise NotFoundError("WATCHLIST_NOT_FOUND", f"Unknown watchlist: {watchlist_id}")
        self._validate_symbols(conn, body.symbols)
        self._watchlists.set_symbols(conn, watchlist_id, body.symbols)
        return self._to_response(conn, row)
