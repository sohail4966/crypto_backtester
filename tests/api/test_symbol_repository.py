"""Tests for symbol repository SQL parameter binding."""

from __future__ import annotations

from unittest.mock import MagicMock

from api.repositories import queries
from api.repositories.symbol_repository import SymbolRepository


def test_list_symbols_without_query_skips_search_filter() -> None:
    """Unfiltered symbol list uses the no-search SQL (avoids untyped NULL params)."""
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchall.return_value = []
    conn.cursor.return_value.__enter__.return_value = cursor

    SymbolRepository().list_symbols(conn, query=None, active_only=True)

    cursor.execute.assert_called_once_with(queries.SELECT_SYMBOLS, (True,))


def test_list_symbols_with_query_uses_search_sql() -> None:
    """Search filter uses ILIKE parameters with explicit patterns."""
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchall.return_value = []
    conn.cursor.return_value.__enter__.return_value = cursor

    SymbolRepository().list_symbols(conn, query="btc", active_only=False)

    cursor.execute.assert_called_once_with(
        queries.SELECT_SYMBOLS_SEARCH,
        ("%btc%", "%btc%", False),
    )
