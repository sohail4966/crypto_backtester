"""
Live candle WebSocket — DB-tail of latest closed bars.

Protocol:

    Client → server: subscribe, unsubscribe, ping
    Server → client: subscribed, candle, pong, error

v1 polls TimescaleDB for the latest closed candle per subscription; no exchange stream.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api import settings
from api.exceptions import ValidationError
from api.schemas.candles import Bar
from api.services.candle_service import CandleService
from api.services.timeframes import validate_timeframe
from data.db import connect

router = APIRouter()
_candles = CandleService()


def _error_event(code: str, message: str) -> dict[str, Any]:
    """Build a WS error event."""
    return {"type": "error", "code": code, "message": message}


async def _send_json(websocket: WebSocket, payload: dict[str, Any]) -> None:
    """Send one JSON text frame."""
    await websocket.send_text(json.dumps(payload, default=str))


def _latest_bar(symbol: str, timeframe: str) -> Bar | None:
    """
    Load the latest closed candle for symbol+timeframe.

    Returns:
        Bar or None when empty / invalid.
    """
    conn = connect()
    try:
        try:
            validate_timeframe(timeframe)
        except ValueError as exc:
            raise ValidationError("INVALID_TIMEFRAME", str(exc)) from exc
        response = _candles.get_latest_candles(conn, symbol, timeframe, limit=1)
        if not response.bars:
            return None
        return response.bars[-1]
    finally:
        conn.close()


@router.websocket("/ws/live")
async def live_candles_ws(websocket: WebSocket) -> None:
    """
    Subscribe to latest closed candle updates for one or more symbols.

    Polls the DB on ``LIVE_WS_POLL_INTERVAL_MS`` and pushes ``candle`` when
    the latest bar ``time`` changes.
    """
    await websocket.accept()

    # (symbol, timeframe) → last pushed bar time
    last_times: dict[tuple[str, str], int | None] = {}
    timeframe = "1m"
    poll_s = max(0.25, settings.live_ws_poll_interval_ms() / 1000.0)

    async def poll_once() -> None:
        """Poll all subscriptions and push changed candles."""
        for key in list(last_times.keys()):
            symbol, tf = key
            try:
                bar = await asyncio.to_thread(_latest_bar, symbol, tf)
            except ValidationError as exc:
                await _send_json(websocket, _error_event(exc.code, exc.message))
                continue
            except Exception as exc:  # noqa: BLE001 — surface to client, keep loop
                await _send_json(
                    websocket,
                    _error_event("LIVE_POLL_FAILED", str(exc)),
                )
                continue
            if bar is None:
                continue
            prev = last_times.get(key)
            if prev == bar.time:
                continue
            last_times[key] = bar.time
            await _send_json(
                websocket,
                {
                    "type": "candle",
                    "symbol": symbol,
                    "timeframe": tf,
                    "bar": bar.model_dump(),
                },
            )

    try:
        while True:
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=poll_s)
            except TimeoutError:
                if last_times:
                    await poll_once()
                continue

            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await _send_json(websocket, _error_event("INVALID_JSON", "Expected JSON"))
                continue

            action = message.get("action")
            if action == "ping":
                await _send_json(websocket, {"type": "pong"})
                continue

            if action == "subscribe":
                symbols = message.get("symbols") or []
                if not isinstance(symbols, list) or not symbols:
                    await _send_json(
                        websocket,
                        _error_event("INVALID_SUBSCRIBE", "symbols must be a non-empty list"),
                    )
                    continue
                tf = message.get("timeframe") or timeframe
                try:
                    validate_timeframe(tf)
                except ValueError as exc:
                    await _send_json(websocket, _error_event("INVALID_TIMEFRAME", str(exc)))
                    continue
                timeframe = tf
                for symbol in symbols:
                    if not isinstance(symbol, str) or not symbol.strip():
                        continue
                    last_times[(symbol.strip(), timeframe)] = None
                await _send_json(
                    websocket,
                    {
                        "type": "subscribed",
                        "symbols": sorted({s for (s, tf) in last_times if tf == timeframe}),
                        "timeframe": timeframe,
                    },
                )
                # Push current latest immediately
                await poll_once()
                continue

            if action == "unsubscribe":
                symbols = message.get("symbols") or []
                if isinstance(symbols, list):
                    for symbol in symbols:
                        if isinstance(symbol, str):
                            last_times.pop((symbol, timeframe), None)
                await _send_json(
                    websocket,
                    {
                        "type": "subscribed",
                        "symbols": sorted({s for (s, _) in last_times}),
                        "timeframe": timeframe,
                    },
                )
                continue

            await _send_json(
                websocket,
                _error_event("UNKNOWN_ACTION", f"Unknown action: {action}"),
            )
    except WebSocketDisconnect:
        return
