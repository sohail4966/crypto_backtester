"""
Repository for app.symbols catalog reads.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import psycopg

from api.repositories import queries


class SymbolRow:
    """Row from app.symbols."""

    def __init__(
        self,
        symbol: str,
        base: str,
        quote: str,
        is_active: bool,
        sort_order: int,
        created_at: datetime | None,
    ) -> None:
        self.symbol = symbol
        self.base = base
        self.quote = quote
        self.is_active = is_active
        self.sort_order = sort_order
        self.created_at = created_at


def _row_to_symbol(row: tuple[Any, ...]) -> SymbolRow:
    """Map a database row to SymbolRow."""
    return SymbolRow(
        symbol=row[0],
        base=row[1],
        quote=row[2],
        is_active=row[3],
        sort_order=row[4],
        created_at=row[5],
    )


class SymbolRepository:
    """Read symbols from app.symbols."""

    def list_symbols(
        self,
        conn: psycopg.Connection,
        query: str | None = None,
        active_only: bool = True,
    ) -> list[SymbolRow]:
        """
        List symbols with optional search filter.

        Args:
            conn: Database connection.
            query: Optional search string for symbol/base.
            active_only: When True, return only active symbols.

        Returns:
            Matching symbol rows ordered by sort_order.
        """
        pattern = f"%{query}%" if query else None
        with conn.cursor() as cur:
            cur.execute(
                queries.SELECT_SYMBOLS,
                (pattern, pattern, pattern, active_only),
            )
            return [_row_to_symbol(row) for row in cur.fetchall()]

    def get_symbol(self, conn: psycopg.Connection, symbol: str) -> SymbolRow | None:
        """
        Fetch one symbol by name.

        Args:
            conn: Database connection.
            symbol: Trading pair identifier.

        Returns:
            Symbol row or None if missing.
        """
        with conn.cursor() as cur:
            cur.execute(queries.SELECT_SYMBOL_BY_NAME, (symbol,))
            row = cur.fetchone()
            if row is None:
                return None
            return _row_to_symbol(row)
