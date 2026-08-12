"""
Live candle WebSocket — DB-tail of latest closed bars.

Protocol:

    Client → server: subscribe, unsubscribe, ping
    Server → client: subscribed, candle, pong, error

v1 polls TimescaleDB for the latest closed candle per subscription; no exchange stream.
No authentication.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api import settings
from api.deps import acquire_ws_slot, release_ws_slot, ws_slot_key
from api.exceptions import NotFoundError, ValidationError
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


def _latest_bars(
    conn,
    subscriptions: list[tuple[str, str]],
) -> tuple[dict[tuple[str, str], Bar | None], list[tuple[str, str]]]:
    """
    Load latest closed bars for all subscriptions on one shared connection.

    Groups by timeframe and uses ``WHERE symbol = ANY(%)`` for ``1m`` (G-009).
    Returns ``(results, invalid_keys)`` — invalid keys are subscriptions whose
    symbol is not in the active catalog. They are surfaced once by ``poll_once``
    so a single bad subscription does not tear down the poll loop (BE-L2-002).
    """
    results: dict[tuple[str, str], Bar | None] = {}
    invalid: list[tuple[str, str]] = []
    by_tf: dict[str, list[str]] = {}
    for symbol, timeframe in subscriptions:
        try:
            validate_timeframe(timeframe)
        except ValueError as exc:
            raise ValidationError("INVALID_TIMEFRAME", str(exc)) from exc
        by_tf.setdefault(timeframe, []).append(symbol)

    for timeframe, symbols in by_tf.items():
        try:
            batch = _candles.get_latest_candles_batch(conn, symbols, timeframe)
        except NotFoundError:
            # Fall back to per-symbol queries so one unknown symbol cannot
            # blank the whole timeframe group (BE-L2-002).
            batch = {}
            for symbol in symbols:
                try:
                    single = _candles.get_latest_candles_batch(conn, [symbol], timeframe)
                except NotFoundError:
                    invalid.append((symbol, timeframe))
                    results[(symbol, timeframe)] = None
                    continue
                batch.update(single)
        for symbol, bar in batch.items():
            results[(symbol, timeframe)] = bar
    return results, invalid


@router.websocket("/ws/live")
async def live_candles_ws(websocket: WebSocket) -> None:
    """
    Subscribe to latest closed candle updates for one or more symbols.

    Polls the DB on ``LIVE_WS_POLL_INTERVAL_MS`` and pushes ``candle`` when
    the latest bar ``time`` changes. No AuthN.
    """
    slot_key = ws_slot_key(websocket)
    try:
        acquire_ws_slot(slot_key)
    except ValidationError as exc:
        await websocket.close(code=4429, reason=exc.code)
        return

    # BE-L2-012: the acquire above is now paired with a try/finally that always
    # releases the slot, including when websocket.accept() or the poll setup
    # raise before the main loop starts.
    slot_released = False
    db_conn = None

    # (symbol, timeframe) → last pushed bar time
    last_times: dict[tuple[str, str], int | None] = {}
    # Keys already reported as invalid so we do not spam INVALID_SYMBOL every poll.
    reported_invalid: set[tuple[str, str]] = set()
    timeframe = "1m"
    poll_s = max(0.25, settings.live_ws_poll_interval_ms() / 1000.0)

    async def poll_once() -> None:
        """Poll all subscriptions and push changed candles."""
        keys = list(last_times.keys())
        if not keys:
            return
        try:
            bars, invalid = await asyncio.to_thread(_latest_bars, db_conn, keys)
        except ValidationError as exc:
            await _send_json(websocket, _error_event(exc.code, exc.message))
            return
        except Exception as exc:  # noqa: BLE001 — surface to client, keep loop
            await _send_json(
                websocket,
                _error_event("LIVE_POLL_FAILED", str(exc)),
            )
            return

        for key in invalid:
            if key in reported_invalid:
                continue
            reported_invalid.add(key)
            symbol, tf = key
            await _send_json(
                websocket,
                _error_event("INVALID_SYMBOL", f"Unknown symbol: {symbol}"),
            )
            last_times.pop(key, None)

        for key, bar in bars.items():
            if bar is None:
                continue
            prev = last_times.get(key)
            if prev == bar.time:
                continue
            last_times[key] = bar.time
            symbol, tf = key
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
        # One shared DB connection for the socket lifetime (BE-019). Autocommit
        # keeps a transient DB failure or NotFoundError from leaving the
        # connection in InFailedSqlTransaction and poisoning every subsequent
        # poll (BE-L2-002).
        db_conn = connect()
        db_conn.autocommit = True

        await websocket.accept()

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
    finally:
        if db_conn is not None:
            try:
                db_conn.close()
            except Exception:
                pass
        if not slot_released:
            slot_released = True
            release_ws_slot(slot_key)
