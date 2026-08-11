"""
Repository for app.watchlists and watchlist_symbols.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

import psycopg

from api.repositories import queries


class WatchlistRow:
    """Row from app.watchlists."""

    def __init__(
        self,
        id: UUID,
        user_id: UUID,
        name: str,
        is_default: bool,
        sort_order: int,
        created_at: datetime,
    ) -> None:
        self.id = id
        self.user_id = user_id
        self.name = name
        self.is_default = is_default
        self.sort_order = sort_order
        self.created_at = created_at


def _row_to_watchlist(row: tuple[Any, ...]) -> WatchlistRow:
    """Map a database row to WatchlistRow."""
    return WatchlistRow(
        id=row[0],
        user_id=row[1],
        name=row[2],
        is_default=row[3],
        sort_order=row[4],
        created_at=row[5],
    )


class WatchlistRepository:
    """CRUD for watchlists scoped to a user."""

    def create(
        self,
        conn: psycopg.Connection,
        user_id: UUID,
        name: str,
        is_default: bool = False,
        sort_order: int = 0,
        *,
        commit: bool = True,
    ) -> WatchlistRow:
        """Insert a watchlist header row."""
        with conn.cursor() as cur:
            cur.execute(queries.INSERT_WATCHLIST, (user_id, name, is_default, sort_order))
            row = cur.fetchone()
            if commit:
                conn.commit()
            assert row is not None
            return _row_to_watchlist(row)

    def list_by_user(self, conn: psycopg.Connection, user_id: UUID) -> list[WatchlistRow]:
        """List all watchlists for a user."""
        with conn.cursor() as cur:
            cur.execute(queries.SELECT_WATCHLISTS_BY_USER, (user_id,))
            return [_row_to_watchlist(row) for row in cur.fetchall()]

    def get_by_id(
        self,
        conn: psycopg.Connection,
        user_id: UUID,
        watchlist_id: UUID,
    ) -> WatchlistRow | None:
        """Fetch one watchlist owned by user."""
        with conn.cursor() as cur:
            cur.execute(queries.SELECT_WATCHLIST_BY_ID, (watchlist_id, user_id))
            row = cur.fetchone()
            if row is None:
                return None
            return _row_to_watchlist(row)

    def update(
        self,
        conn: psycopg.Connection,
        user_id: UUID,
        watchlist_id: UUID,
        name: str | None,
        is_default: bool | None,
        sort_order: int | None,
        *,
        commit: bool = True,
    ) -> WatchlistRow | None:
        """
        Patch watchlist metadata.

        When setting ``is_default=True``, uses an atomic CTE so a missed update
        cannot clear all defaults (BE-013).
        """
        with conn.cursor() as cur:
            if is_default:
                cur.execute(
                    queries.SET_DEFAULT_WATCHLIST,
                    (name, sort_order, watchlist_id, user_id),
                )
            else:
                cur.execute(
                    queries.UPDATE_WATCHLIST,
                    (name, is_default, sort_order, watchlist_id, user_id),
                )
            row = cur.fetchone()
            if commit:
                if row is None:
                    conn.rollback()
                else:
                    conn.commit()
            if row is None:
                return None
            return _row_to_watchlist(row)

    def delete(
        self,
        conn: psycopg.Connection,
        user_id: UUID,
        watchlist_id: UUID,
        *,
        commit: bool = True,
    ) -> bool:
        """Delete a watchlist."""
        with conn.cursor() as cur:
            cur.execute(queries.DELETE_WATCHLIST, (watchlist_id, user_id))
            if commit:
                conn.commit()
            return cur.rowcount > 0

    def get_symbols(self, conn: psycopg.Connection, watchlist_id: UUID) -> list[str]:
        """Return ordered symbols for a watchlist."""
        with conn.cursor() as cur:
            cur.execute(queries.SELECT_WATCHLIST_SYMBOLS, (watchlist_id,))
            return [row[0] for row in cur.fetchall()]

    def set_symbols(
        self,
        conn: psycopg.Connection,
        watchlist_id: UUID,
        symbols: list[str],
        *,
        commit: bool = True,
    ) -> None:
        """Replace all symbols in a watchlist."""
        with conn.cursor() as cur:
            cur.execute(queries.DELETE_WATCHLIST_SYMBOLS, (watchlist_id,))
            for index, symbol in enumerate(symbols):
                cur.execute(queries.INSERT_WATCHLIST_SYMBOL, (watchlist_id, symbol, index))
            if commit:
                conn.commit()
