"""
Bar replay WebSocket handler (v2 — client-owned playback clock).

Protocol summary:

    Client → server: play, pause, step, seek, set_speed, set_indicators,
                     get_state, refill

    Server → client: replay_state, snapshot, tick_batch, buffer_loading,
                     buffer_ready, buffer_reset, replay_completed, error

The client owns playback timing (``intervalMs = max(50, 1000 / speed)``).
The server pre-slices ``tick_batch`` messages; ``refill`` requests more ticks
when the client queue drops below ``REPLAY_TICK_REFILL_THRESHOLD``.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api import settings
from api.exceptions import ApiError, ValidationError
from api.schemas.indicators import IndicatorSpec
from api.services.replay_engine import ReplayEngine
from api.services.replay_service import ReplayService, get_replay_service
from data.db import connect

router = APIRouter()

# Last connection per session wins; prior socket receives SUPERSEDED + close.
_active_connections: dict[UUID, WebSocket] = {}


def _error_event(code: str, message: str) -> dict[str, Any]:
    """
    Build a WS ``error`` event payload.

    Args:
        code: Machine-readable error code.
        message: Human-readable description.

    Returns:
        JSON-serializable error event.
    """
    return {"type": "error", "code": code, "message": message}


async def _send_json(websocket: WebSocket, payload: dict[str, Any]) -> None:
    """Send one JSON text frame to the client."""
    await websocket.send_text(json.dumps(payload, default=str))


def _replay_state_payload(service: ReplayService, engine: ReplayEngine) -> dict[str, Any]:
    """
    Build a ``replay_state`` event with camelCase field names.

    Args:
        service: Replay service for state serialization.
        engine: Live replay engine.

    Returns:
        JSON-serializable state event.
    """
    return {
        "type": "replay_state",
        **service.to_state_response(engine).model_dump(by_alias=True, mode="json"),
    }


async def _emit_extend_events(
    websocket: WebSocket,
    engine: ReplayEngine,
    extend_status: str,
) -> None:
    """
    Emit buffer lifecycle events after a step batch.

    Args:
        websocket: Client connection.
        engine: Engine after ``step_batch``.
        extend_status: Result from extend logic (``ready``, ``completed``, etc.).
    """
    if extend_status == "ready":
        await _send_json(
            websocket,
            {
                "type": "buffer_ready",
                "bufferEnd": engine.buffer.buffer_end_ts(),
                "latestAvailable": engine.buffer.latest_available_ts,
            },
        )
    if extend_status == "completed" or engine.state == "completed":
        await _send_json(websocket, {"type": "replay_completed"})


async def _send_tick_batch(
    websocket: WebSocket,
    engine: ReplayEngine,
    conn,
    count: int | None = None,
) -> str:
    """
    Advance the engine and emit a ``tick_batch`` (and extend events).

    Emits ``buffer_loading`` before extend when cursor nears prefetch edge.

    Args:
        websocket: Client connection.
        engine: Live replay engine.
        conn: Database connection for forward extend.
        count: Max ticks to slice (default: ``REPLAY_TICK_BATCH_SIZE``).

    Returns:
        Extend status after the batch (``ready``, ``completed``, ``none``, ...).
    """
    if engine.buffer.needs_extend(settings.replay_extend_threshold()):
        await _send_json(websocket, {"type": "buffer_loading"})
    ticks, extend_status = engine.step_batch(conn, count=count)
    if ticks:
        await _send_json(websocket, engine.tick_batch_payload(ticks))
    await _emit_extend_events(websocket, engine, extend_status)
    return extend_status


@router.websocket("/ws/replay/{session_id}")
async def replay_websocket(websocket: WebSocket, session_id: UUID) -> None:
    """
    WebSocket v2 replay control plane for one session.

    On connect: sends ``replay_state`` then ``snapshot``. If session was
    created with ``autoplay``, also sends the first ``tick_batch``.

    Client actions:
        - ``play`` — set playing; send initial ``tick_batch``
        - ``pause`` — pause and checkpoint cursor
        - ``step`` — manual advance (optional ``count``)
        - ``refill`` — top up client tick queue during playback (full batch)
        - ``seek`` — jump to ``to`` unix timestamp
        - ``set_speed`` — update speed multiplier
        - ``set_indicators`` — reload buffer with new overlays
        - ``get_state`` — return current ``replay_state``

    Concurrent connections: last connection wins; prior gets ``SUPERSEDED``.

    Args:
        websocket: Client WebSocket.
        session_id: Replay session UUID from ``POST /replay/sessions``.
    """
    service = get_replay_service()
    prior = _active_connections.get(session_id)
    if prior is not None:
        try:
            await _send_json(prior, _error_event("SUPERSEDED", "A newer connection replaced this session"))
            await prior.close(code=4401)
        except Exception:
            pass

    await websocket.accept()
    _active_connections[session_id] = websocket

    try:
        with connect() as conn:
            engine = service.get_engine(conn, session_id)
            await _send_json(websocket, _replay_state_payload(service, engine))
            await _send_json(websocket, engine.snapshot_payload())
            if service.consume_autoplay(session_id):
                engine.state = "playing"
                await _send_json(websocket, _replay_state_payload(service, engine))
                await _send_tick_batch(websocket, engine, conn)
                service.checkpoint(conn, session_id)

            while True:
                raw = await websocket.receive_text()
                payload = json.loads(raw)
                action = payload.get("action")
                engine = service.get_engine(conn, session_id)

                if action == "play":
                    speed = payload.get("speed")
                    if speed is not None:
                        engine.set_speed(float(speed))
                    engine.state = "playing"
                    await _send_json(websocket, _replay_state_payload(service, engine))
                    await _send_tick_batch(websocket, engine, conn)
                    service.checkpoint(conn, session_id)
                    continue

                if action == "pause":
                    engine.state = "paused"
                    service.checkpoint(conn, session_id, force=True)
                    await _send_json(websocket, _replay_state_payload(service, engine))
                    continue

                if action in ("step", "refill"):
                    count = int(payload.get("count", settings.replay_tick_batch_size()))
                    if action == "refill":
                        count = settings.replay_tick_batch_size()
                    await _send_tick_batch(websocket, engine, conn, count=count)
                    await _send_json(websocket, _replay_state_payload(service, engine))
                    service.checkpoint(conn, session_id)
                    if engine.state == "completed":
                        service.checkpoint(conn, session_id, force=True)
                    continue

                if action == "seek":
                    to_ts = payload.get("to")
                    if to_ts is None:
                        await _send_json(websocket, _error_event("INVALID_REQUEST", "seek requires to"))
                        continue
                    try:
                        reloaded = engine.seek(conn, int(to_ts))
                    except ValidationError as exc:
                        await _send_json(websocket, _error_event(exc.code, exc.message))
                        continue
                    if reloaded:
                        await _send_json(websocket, {"type": "buffer_reset"})
                        await _send_json(websocket, engine.snapshot_payload())
                    await _send_json(websocket, _replay_state_payload(service, engine))
                    service.checkpoint(conn, session_id, force=True)
                    continue

                if action == "set_speed":
                    speed = payload.get("speed")
                    if speed is None:
                        await _send_json(
                            websocket,
                            _error_event("INVALID_REQUEST", "set_speed requires speed"),
                        )
                        continue
                    try:
                        engine.set_speed(float(speed))
                    except ValidationError as exc:
                        await _send_json(websocket, _error_event(exc.code, exc.message))
                        continue
                    await _send_json(websocket, _replay_state_payload(service, engine))
                    continue

                if action == "set_indicators":
                    raw_specs = payload.get("indicators", [])
                    specs = [IndicatorSpec.model_validate(item) for item in raw_specs]
                    was_playing = engine.state == "playing"
                    engine = service.update_indicators(conn, session_id, specs)
                    await _send_json(websocket, {"type": "buffer_reset"})
                    await _send_json(websocket, engine.snapshot_payload())
                    await _send_json(websocket, _replay_state_payload(service, engine))
                    if was_playing:
                        engine.state = "playing"
                    service.checkpoint(conn, session_id, force=True)
                    continue

                if action == "get_state":
                    await _send_json(websocket, _replay_state_payload(service, engine))
                    continue

                await _send_json(websocket, _error_event("INVALID_ACTION", f"Unknown action: {action}"))

    except WebSocketDisconnect:
        pass
    except ApiError as exc:
        await _send_json(websocket, _error_event(exc.code, exc.message))
    finally:
        if _active_connections.get(session_id) is websocket:
            del _active_connections[session_id]
        try:
            with connect() as conn:
                service.checkpoint(conn, session_id, force=True)
        except Exception:
            pass
