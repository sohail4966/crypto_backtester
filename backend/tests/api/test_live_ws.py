"""Tests for live candle WebSocket (Phase 11)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.schemas.candles import Bar


@patch("api.ws.live._latest_bar")
def test_live_ws_subscribe_pushes_candle(
    mock_latest: MagicMock,
    client: TestClient,
) -> None:
    bar = Bar(time=1_700_000_000, open=1, high=2, low=0.5, close=1.5, volume=10)
    mock_latest.return_value = bar

    with client.websocket_connect("/ws/live") as ws:
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
