"""
Tests for user and watchlist services.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from api.exceptions import ValidationError
from api.repositories.user_repository import UserRepository, UserRow
from api.repositories.watchlist_repository import WatchlistRepository, WatchlistRow
from api.schemas.users import UserCreate
from tests.api.conftest import make_symbol_response
from api.schemas.watchlists import WatchlistCreate
from api.services.symbol_service import SymbolService
from api.services.user_service import UserService
from api.services.watchlist_service import WatchlistService


def _user_row() -> UserRow:
    """Sample user row."""
    now = datetime(2024, 1, 1, tzinfo=UTC)
    return UserRow(uuid4(), "Alice", "alice@example.com", now, now)


def test_user_create_provisions_default_watchlist() -> None:
    """Creating a user also creates a default watchlist."""
    users = MagicMock(spec=UserRepository)
    watchlists = MagicMock(spec=WatchlistRepository)
    user = _user_row()
    users.create.return_value = user
    watchlists.create.return_value = WatchlistRow(
        uuid4(),
        user.id,
        "Default",
        True,
        0,
        datetime(2024, 1, 1, tzinfo=UTC),
    )

    symbol_service = MagicMock(spec=SymbolService)
    symbol_service.list_symbols.return_value = [
        make_symbol_response("BTC/USDT", "BTC", "USDT", sort_order=1),
        make_symbol_response("ETH/USDT", "ETH", "USDT", sort_order=2),
    ]

    service = UserService(
        user_repository=users,
        watchlist_repository=watchlists,
        symbol_service=symbol_service,
    )
    result = service.create(MagicMock(), UserCreate(name="Alice", email="alice@example.com"))
    assert result.email == "alice@example.com"
    watchlists.create.assert_called_once()
    watchlists.set_symbols.assert_called_once()


def test_watchlist_invalid_symbol_raises() -> None:
    """Invalid symbol in watchlist raises validation error."""
    from api.repositories.symbol_repository import SymbolRepository

    users = MagicMock(spec=UserRepository)
    users.get_by_id.return_value = _user_row()
    watchlists = MagicMock(spec=WatchlistRepository)
    symbols = MagicMock(spec=SymbolRepository)
    symbols.get_symbol.return_value = None

    service = WatchlistService(
        watchlist_repository=watchlists,
        user_repository=users,
        symbol_repository=symbols,
    )
    user_id = uuid4()
    with pytest.raises(ValidationError):
        service.create_watchlist(
            MagicMock(),
            user_id,
            WatchlistCreate(name="Bad", symbols=["FOO/USDT"]),
        )
