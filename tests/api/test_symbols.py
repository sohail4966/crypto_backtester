"""
Tests for symbol repository and service.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from api.repositories.symbol_repository import SymbolRepository
from api.services.symbol_service import SymbolService


def test_symbol_service_lists_rows(sample_symbols) -> None:
    """Symbol service maps repository rows to responses."""
    repo = MagicMock(spec=SymbolRepository)
    repo.list_symbols.return_value = sample_symbols
    service = SymbolService(repository=repo)
    result = service.list_symbols(MagicMock())
    assert len(result) == 3
    assert result[0].symbol == "BTC/USDT"


def test_symbol_service_not_found() -> None:
    """Missing symbol raises NotFoundError."""
    import pytest

    from api.exceptions import NotFoundError

    repo = MagicMock(spec=SymbolRepository)
    repo.get_symbol.return_value = None
    service = SymbolService(repository=repo)
    with pytest.raises(NotFoundError):
        service.get_symbol(MagicMock(), "FOO/USDT")
