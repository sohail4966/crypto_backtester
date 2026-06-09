"""
Symbol catalog service.
"""

from __future__ import annotations

import psycopg

from api.exceptions import NotFoundError
from api.repositories.symbol_repository import SymbolRepository
from api.schemas.symbols import SymbolResponse


class SymbolService:
    """Business logic for symbol catalog endpoints."""

    def __init__(self, repository: SymbolRepository | None = None) -> None:
        self._repository = repository or SymbolRepository()

    def list_symbols(
        self,
        conn: psycopg.Connection,
        query: str | None = None,
        active_only: bool = True,
    ) -> list[SymbolResponse]:
        """Return symbol catalog rows."""
        rows = self._repository.list_symbols(conn, query=query, active_only=active_only)
        return [
            SymbolResponse(
                symbol=row.symbol,
                base=row.base,
                quote=row.quote,
                is_active=row.is_active,
                sort_order=row.sort_order,
                created_at=row.created_at,
            )
            for row in rows
        ]

    def get_symbol(self, conn: psycopg.Connection, symbol: str) -> SymbolResponse:
        """Return one symbol or raise NotFoundError."""
        row = self._repository.get_symbol(conn, symbol)
        if row is None:
            raise NotFoundError("SYMBOL_NOT_FOUND", f"Unknown symbol: {symbol}")
        return SymbolResponse(
            symbol=row.symbol,
            base=row.base,
            quote=row.quote,
            is_active=row.is_active,
            sort_order=row.sort_order,
            created_at=row.created_at,
        )

    def require_active_symbol(self, conn: psycopg.Connection, symbol: str) -> SymbolResponse:
        """Ensure symbol exists and is active."""
        row = self.get_symbol(conn, symbol)
        if not row.is_active:
            raise NotFoundError("SYMBOL_INACTIVE", f"Symbol is inactive: {symbol}")
        return row
