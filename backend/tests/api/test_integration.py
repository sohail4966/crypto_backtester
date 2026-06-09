"""
Light integration tests with mocked persistence layer.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pandas as pd
from fastapi.testclient import TestClient

from api.repositories.symbol_repository import SymbolRow


@patch("api.deps.connect")
@patch("api.services.candle_service.get_candles")
def test_integration_symbols_and_candles(
    mock_get_candles: MagicMock,
    mock_connect: MagicMock,
    client: TestClient,
) -> None:
    """Symbols list and candle fetch return expected shapes."""
    now = datetime(2024, 1, 1, tzinfo=UTC)
    rows = [
        SymbolRow("BTC/USDT", "BTC", "USDT", True, 1, now),
        SymbolRow("ETH/USDT", "ETH", "USDT", True, 2, now),
        SymbolRow("SOL/USDT", "SOL", "USDT", True, 3, now),
    ]

    conn = MagicMock()
    mock_connect.return_value = conn

    with patch("api.repositories.symbol_repository.SymbolRepository.list_symbols", return_value=rows):
        symbols_resp = client.get("/api/v1/symbols")
        assert symbols_resp.status_code == 200
        assert len(symbols_resp.json()) == 3

    ts = pd.to_datetime(["2024-01-01", "2024-01-02"], utc=True)
    mock_get_candles.return_value = pd.DataFrame(
        {
            "ts": ts,
            "open": [1.0, 1.1],
            "high": [2.0, 2.1],
            "low": [0.5, 0.6],
            "close": [1.5, 1.6],
            "volume": [100.0, 110.0],
        }
    )
    with patch("api.repositories.symbol_repository.SymbolRepository.get_symbol", return_value=rows[0]):
        candles_resp = client.get(
            "/api/v1/candles/BTC/USDT",
            params={"timeframe": "1d", "from": 1704067200, "to": 1706745600},
        )
        assert candles_resp.status_code == 200
        assert len(candles_resp.json()["bars"]) == 2


@patch("api.deps.connect")
def test_integration_indicators_catalog(mock_connect: MagicMock, client: TestClient) -> None:
    """Indicator catalog is reachable."""
    mock_connect.return_value = MagicMock()
    response = client.get("/api/v1/indicators")
    assert response.status_code == 200
    keys = {item["key"] for item in response.json()}
    assert "RSI" in keys
    assert "SMA" in keys
