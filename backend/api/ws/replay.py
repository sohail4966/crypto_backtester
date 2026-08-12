"""
Bar replay WebSocket handler (v2 — client-owned playback clock).

No AuthN. DB connections are opened per critical section, not for
the full socket lifetime (BE-018).
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api import settings
from api.deps import acquire_ws_slot, release_ws_slot, ws_slot_key
from api.exceptions import ApiError, NotFoundError, ValidationError
from api.schemas.indicators import IndicatorSpec
from api.services.replay_engine import ReplayEngine
from api.services.replay_service import ReplayService, get_replay_service
from data.db import connect

router = APIRouter()

# Distinct application close codes:
#   4402 SUPERSEDED   — same session opened in another tab
#   4404 NOT_FOUND    — session missing
WS_SUPERSEDED = 4402
WS_REPLAY_NOT_FOUND = 4404

_active_connections: dict[UUID, WebSocket] = {}
# Guards the check-then-supersede-then-store sequence against concurrent
# connects to the same ``session_id`` (BE-L2-013).
_active_lock = asyncio.Lock()


def _error_event(code: str, message: str) -> dict[str, Any]:
    """Build a WS ``error`` event payload."""
    return {"type": "error", "code": code, "message": message}


async def _send_json(websocket: WebSocket, payload: dict[str, Any]) -> None:
    """Send one JSON text frame to the client."""
    await websocket.send_text(json.dumps(payload, default=str))


def _replay_state_payload(service: ReplayService, engine: ReplayEngine) -> dict[str, Any]:
    """Build a ``replay_state`` event with camelCase field names."""
    return {
        "type": "replay_state",
        **service.to_state_response(engine).model_dump(by_alias=True, mode="json"),
    }


async def _emit_extend_events(
    websocket: WebSocket,
    engine: ReplayEngine,
    extend_status: str,
) -> None:
    """Emit buffer lifecycle events after a step batch."""
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
    """Advance the engine and emit a ``tick_batch`` (and extend events)."""
    if engine.buffer.needs_extend(settings.replay_extend_threshold()):
        await _send_json(websocket, {"type": "buffer_loading"})
    ticks, extend_status = engine.step_batch(conn, count=count)
    await _send_json(websocket, engine.tick_batch_payload(ticks))
    await _emit_extend_events(websocket, engine, extend_status)
    return extend_status


@router.websocket("/ws/replay/{session_id}")
async def replay_websocket(
    websocket: WebSocket,
    session_id: UUID,
) -> None:
    """
    WebSocket v2 replay control plane for one session.

    No AuthN. Session must exist.
    """
    service = get_replay_service()
    try:
        with connect() as conn:
            service.require_session(conn, session_id)
    except NotFoundError:
        await websocket.close(code=WS_REPLAY_NOT_FOUND, reason="REPLAY_NOT_FOUND")
        return

    slot_key = ws_slot_key(websocket)
    try:
        acquire_ws_slot(slot_key)
    except ValidationError as exc:
        await websocket.close(code=4429, reason=exc.code)
        return

    # BE-L2-012: acquire is paired with the try/finally below so an exception
    # in ``accept()`` or the initial replay-state fetch does not leak the slot.
    slot_released = False

    prior: WebSocket | None = None
    async with _active_lock:
        prior = _active_connections.get(session_id)
        _active_connections[session_id] = websocket
    if prior is not None:
        try:
            await _send_json(
                prior,
                _error_event("SUPERSEDED", "A newer connection replaced this session"),
            )
            await prior.close(code=WS_SUPERSEDED, reason="SUPERSEDED")
        except Exception:
            pass

    try:
        await websocket.accept()

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
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await _send_json(websocket, _error_event("INVALID_JSON", "Expected JSON"))
                continue

            action = payload.get("action")

            with connect() as conn:
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
    except NotFoundError:
        try:
            await websocket.close(code=WS_REPLAY_NOT_FOUND, reason="REPLAY_NOT_FOUND")
        except Exception:
            pass
    except ApiError as exc:
        try:
            await _send_json(websocket, _error_event(exc.code, exc.message))
        except Exception:
            pass
    finally:
        async with _active_lock:
            if _active_connections.get(session_id) is websocket:
                del _active_connections[session_id]
        if not slot_released:
            slot_released = True
            release_ws_slot(slot_key)
        try:
            with connect() as conn:
                service.checkpoint(conn, session_id, force=True)
        except Exception:
            pass
