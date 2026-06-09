"""
Bar replay WebSocket handler.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api import settings
from api.exceptions import ApiError, ValidationError
from api.schemas.indicators import IndicatorSpec
from api.services.replay_service import get_replay_service
from data.db import connect

router = APIRouter()


def _error_event(code: str, message: str) -> dict[str, Any]:
    """Build WS error payload."""
    return {"type": "error", "code": code, "message": message}


async def _send_json(websocket: WebSocket, payload: dict[str, Any]) -> None:
    """Send JSON message to client."""
    await websocket.send_text(json.dumps(payload, default=str))


async def _autoplay_loop(websocket: WebSocket, session_id: UUID) -> None:
    """Emit bars at configured speed until pause, complete, or disconnect."""
    service = get_replay_service()
    min_interval = settings.replay_min_step_interval_ms() / 1000.0
    while True:
        session = service.get_session(session_id)
        if session.state != "playing":
            break
        bar, indicators, completed = service.step(session)
        if bar is not None:
            await _send_json(websocket, {"type": "candle", "bar": bar.model_dump()})
            await _send_json(
                websocket,
                {
                    "type": "indicators",
                    "series": [s.model_dump() for s in indicators],
                },
            )
        await _send_json(
            websocket,
            {"type": "replay_state", **service.to_state_response(session).model_dump()},
        )
        if completed:
            await _send_json(websocket, {"type": "replay_completed"})
            break
        interval = max(min_interval, 1.0 / session.speed)
        await asyncio.sleep(interval)


@router.websocket("/ws/replay/{session_id}")
async def replay_websocket(websocket: WebSocket, session_id: UUID) -> None:
    """
    Control bar replay and receive candle + indicator events.

    Args:
        websocket: Client connection.
        session_id: In-memory replay session identifier.
    """
    service = get_replay_service()
    await websocket.accept()
    autoplay_task: asyncio.Task[None] | None = None
    try:
        session = service.get_session(session_id)
        await _send_json(
            websocket,
            {"type": "replay_state", **service.to_state_response(session).model_dump()},
        )

        while True:
            raw = await websocket.receive_text()
            payload = json.loads(raw)
            action = payload.get("action")
            session = service.get_session(session_id)

            if autoplay_task and not autoplay_task.done():
                autoplay_task.cancel()
                autoplay_task = None
                session.state = "paused"

            if action == "play":
                speed = payload.get("speed")
                if speed is not None:
                    service.set_speed(session, float(speed))
                session.state = "playing"
                autoplay_task = asyncio.create_task(_autoplay_loop(websocket, session_id))
                continue

            if action == "pause":
                session.state = "paused"
                await _send_json(
                    websocket,
                    {"type": "replay_state", **service.to_state_response(session).model_dump()},
                )
                continue

            if action == "step":
                count = int(payload.get("count", 1))
                bar, indicators, completed = service.step(session, count=count)
                if bar is not None:
                    await _send_json(websocket, {"type": "candle", "bar": bar.model_dump()})
                    await _send_json(
                        websocket,
                        {
                            "type": "indicators",
                            "series": [s.model_dump() for s in indicators],
                        },
                    )
                await _send_json(
                    websocket,
                    {"type": "replay_state", **service.to_state_response(session).model_dump()},
                )
                if completed:
                    await _send_json(websocket, {"type": "replay_completed"})
                continue

            if action == "seek":
                to_ts = payload.get("to")
                if to_ts is None:
                    await _send_json(websocket, _error_event("INVALID_REQUEST", "seek requires to"))
                    continue
                try:
                    service.seek(session, int(to_ts))
                except ValidationError as exc:
                    await _send_json(websocket, _error_event(exc.code, exc.message))
                    continue
                await _send_json(
                    websocket,
                    {"type": "replay_state", **service.to_state_response(session).model_dump()},
                )
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
                    service.set_speed(session, float(speed))
                except ValidationError as exc:
                    await _send_json(websocket, _error_event(exc.code, exc.message))
                    continue
                await _send_json(
                    websocket,
                    {"type": "replay_state", **service.to_state_response(session).model_dump()},
                )
                continue

            if action == "set_step_timeframe":
                step_tf = payload.get("step_timeframe")
                if step_tf is None:
                    await _send_json(
                        websocket,
                        _error_event("INVALID_REQUEST", "set_step_timeframe required"),
                    )
                    continue
                with connect() as conn:
                    try:
                        service.set_step_timeframe(conn, session, str(step_tf))
                    except (ValidationError, ApiError) as exc:
                        await _send_json(websocket, _error_event(exc.code, exc.message))
                        continue
                await _send_json(
                    websocket,
                    {"type": "replay_state", **service.to_state_response(session).model_dump()},
                )
                continue

            if action == "set_indicators":
                raw_specs = payload.get("indicators", [])
                specs = [IndicatorSpec.model_validate(item) for item in raw_specs]
                service.set_indicators(session, specs)
                await _send_json(
                    websocket,
                    {"type": "replay_state", **service.to_state_response(session).model_dump()},
                )
                continue

            if action == "get_state":
                await _send_json(
                    websocket,
                    {"type": "replay_state", **service.to_state_response(session).model_dump()},
                )
                continue

            await _send_json(websocket, _error_event("INVALID_ACTION", f"Unknown action: {action}"))

    except WebSocketDisconnect:
        pass
    except ApiError as exc:
        await _send_json(websocket, _error_event(exc.code, exc.message))
    finally:
        if autoplay_task and not autoplay_task.done():
            autoplay_task.cancel()
