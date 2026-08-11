"""Tests for live candle WebSocket (Phase 11 / BE-004 / BE-019)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from api.auth import create_access_token
from api.repositories.user_repository import UserRow
from api.schemas.candles import Bar


def _user() -> UserRow:
    now = datetime(2024, 1, 1, tzinfo=UTC)
    return UserRow(
        id=uuid4(),
        name="Live",
        email="live@example.com",
        password_hash="x",
        created_at=now,
        updated_at=now,
    )


@patch("api.ws.live.connect")
@patch("api.ws.live._latest_bars")
@patch("api.ws.live.user_from_ws_token")
def test_live_ws_subscribe_pushes_candle(
    mock_user: MagicMock,
    mock_latest: MagicMock,
    mock_connect: MagicMock,
    client: TestClient,
) -> None:
    user = _user()
    mock_user.return_value = user
    mock_connect.return_value = MagicMock()
    bar = Bar(time=1_700_000_000, open=1, high=2, low=0.5, close=1.5, volume=10)
    mock_latest.return_value = {("BTC/USDT", "1m"): bar}
    token = create_access_token(user_id=user.id, email=user.email)

    with client.websocket_connect(f"/ws/live?token={token}") as ws:
        ws.send_json(
            {"action": "subscribe", "symbols": ["BTC/USDT"], "timeframe": "1m"}
        )
        subscribed = ws.receive_json()
        assert subscribed["type"] == "subscribed"
        assert "BTC/USDT" in subscribed["symbols"]
        assert subscribed["timeframe"] == "1m"

        candle = ws.receive_json()
        assert candle["type"] == "candle"
        assert candle["symbol"] == "BTC/USDT"
        assert candle["bar"]["time"] == bar.time
        assert candle["bar"]["close"] == bar.close

        ws.send_json({"action": "ping"})
        pong = ws.receive_json()
        assert pong["type"] == "pong"
