"""Tests for Phase 4b symbol v2 shape and search alias."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.repositories.symbol_repository import SymbolRow


def _btc_row() -> SymbolRow:
    now = datetime(2024, 1, 1, tzinfo=UTC)
    return SymbolRow(
        "BTC/USDT",
        "BTC",
        "USDT",
        True,
        1,
        now,
        exchange="binance",
        tick_size=0.01,
        lot_size=0.00001,
        asset_type="spot",
    )


@patch("api.deps.connect")
def test_symbols_return_v2_fields(mock_connect: MagicMock, client: TestClient) -> None:
    """List symbols includes structured v2 fields."""
    mock_connect.return_value = MagicMock()
    row = _btc_row()
    with patch("api.repositories.symbol_repository.SymbolRepository.list_symbols", return_value=[row]):
        response = client.get("/api/v1/symbols")
    assert response.status_code == 200
    body = response.json()[0]
    assert body["id"] == "BTC/USDT"
    assert body["ticker"] == "BTC/USDT"
    assert body["exchange"] == "binance"
    assert body["baseAsset"] == "BTC"
    assert body["quoteAsset"] == "USDT"
    assert body["tickSize"] == 0.01
    assert body["lotSize"] == 0.00001
    assert body["type"] == "spot"
    assert body["active"] is True
    assert body["symbol"] == "BTC/USDT"


@patch("api.deps.connect")
def test_symbols_search_alias(mock_connect: MagicMock, client: TestClient) -> None:
    """GET /symbols/search mirrors list handler."""
    mock_connect.return_value = MagicMock()
    row = _btc_row()
    with patch("api.repositories.symbol_repository.SymbolRepository.list_symbols", return_value=[row]) as mock_list:
        response = client.get("/api/v1/symbols/search", params={"q": "btc"})
    assert response.status_code == 200
    mock_list.assert_called_once()
    assert response.json()[0]["id"] == "BTC/USDT"
