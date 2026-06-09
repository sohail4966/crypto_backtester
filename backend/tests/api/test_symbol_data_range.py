"""Tests for symbol candle data-range metadata."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.repositories.symbol_repository import SymbolRow


@patch("api.routers.symbols._candles.get_data_range")
@patch("api.deps.connect")
def test_symbol_data_range_returns_unix_bounds(
    mock_connect: MagicMock,
    mock_range: MagicMock,
    client: TestClient,
) -> None:
    """GET /symbols/{id}/data-range exposes stored candle bounds."""
    mock_connect.return_value = MagicMock()
    now = datetime(2024, 1, 1, tzinfo=UTC)
    symbol_row = SymbolRow("SOL/USDT", "SOL", "USDT", True, 1, now)
    mock_range.return_value = (
        int(datetime(2023, 1, 1, tzinfo=UTC).timestamp()),
        int(datetime(2024, 1, 1, tzinfo=UTC).timestamp()),
        42,
    )

    with patch(
        "api.repositories.symbol_repository.SymbolRepository.get_symbol",
        return_value=symbol_row,
    ):
        response = client.get(
            "/api/v1/symbols/SOL/USDT/data-range",
            params={"timeframe": "1m"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["symbolId"] == "SOL/USDT"
    assert body["timeframe"] == "1m"
    assert body["earliest"] == int(datetime(2023, 1, 1, tzinfo=UTC).timestamp())
    assert body["latest"] == int(datetime(2024, 1, 1, tzinfo=UTC).timestamp())
    assert body["barCount"] == 42


@patch("api.routers.symbols._candles.get_data_range")
@patch("api.deps.connect")
def test_symbol_data_range_empty_series(
    mock_connect: MagicMock,
    mock_range: MagicMock,
    client: TestClient,
) -> None:
    """Empty series returns null bounds and zero count."""
    mock_connect.return_value = MagicMock()
    now = datetime(2024, 1, 1, tzinfo=UTC)
    symbol_row = SymbolRow("FOO/USDT", "FOO", "USDT", True, 1, now)
    mock_range.return_value = (None, None, 0)

    with patch(
        "api.repositories.symbol_repository.SymbolRepository.get_symbol",
        return_value=symbol_row,
    ):
        response = client.get(
            "/api/v1/symbols/FOO/USDT/data-range",
            params={"timeframe": "1h"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["earliest"] is None
    assert body["latest"] is None
    assert body["barCount"] == 0
