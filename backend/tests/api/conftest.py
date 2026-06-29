"""
Shared fixtures for API tests.
"""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from api.repositories.symbol_repository import SymbolRow
from api.schemas.symbols import SymbolResponse
from api.services.replay_service import get_replay_service
from api.services.symbol_service import SymbolService


def make_symbol_response(
    symbol: str = "BTC/USDT",
    base: str = "BTC",
    quote: str = "USDT",
    *,
    sort_order: int = 1,
) -> SymbolResponse:
    """Build a v2 symbol response for service mocks."""
    return SymbolService.row_to_response(
        SymbolRow(symbol, base, quote, True, sort_order, None),
    )


@pytest.fixture
def mock_conn() -> MagicMock:
    """Mock psycopg connection."""
    conn = MagicMock()
    conn.close = MagicMock()
    return conn


@pytest.fixture
def sample_symbols() -> list[SymbolRow]:
    """Three seeded symbols."""
    now = datetime(2024, 1, 1, tzinfo=UTC)
    return [
        SymbolRow("BTC/USDT", "BTC", "USDT", True, 1, now),
        SymbolRow("ETH/USDT", "ETH", "USDT", True, 2, now),
        SymbolRow("SOL/USDT", "SOL", "USDT", True, 3, now),
    ]


@pytest.fixture
def sample_candles_df() -> pd.DataFrame:
    """Small OHLCV frame for indicator/replay tests."""
    ts = pd.to_datetime(
        ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"],
        utc=True,
    )
    close = pd.Series([100.0, 102.0, 101.0, 105.0, 108.0])
    return pd.DataFrame(
        {
            "ts": ts,
            "open": close - 1,
            "high": close + 2,
            "low": close - 2,
            "close": close,
            "volume": [1000.0, 1100.0, 1200.0, 1300.0, 1400.0],
        }
    )


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """FastAPI test client with migrations skipped."""
    with patch("api.main.run_migrations_on_startup", return_value=0):
        with TestClient(create_app()) as test_client:
            yield test_client


@pytest.fixture(autouse=True)
def clear_replay_sessions() -> Generator[None, None, None]:
    """Reset in-memory replay store between tests."""
    service = get_replay_service()
    service._store.clear_cache()
    yield
    service._store.clear_cache()
