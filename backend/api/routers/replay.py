"""
Replay session REST endpoints (Phase 4c).

Open-ended sessions: create via POST, control playback over WebSocket v2.
"""

from __future__ import annotations

from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends

from api.deps import get_db
from api.schemas.replay import ReplaySessionCreate, ReplaySessionResponse, ReplayStateResponse
from api.services.replay_service import ReplayService, get_replay_service

router = APIRouter(prefix="/replay", tags=["replay"])


def _service() -> ReplayService:
    """Return the process-wide replay service singleton."""
    return get_replay_service()


@router.post("/sessions", response_model=ReplaySessionResponse, status_code=201)
def create_replay_session(
    body: ReplaySessionCreate,
    conn: psycopg.Connection = Depends(get_db),
) -> ReplaySessionResponse:
    """
    Create an open-ended bar replay session.

    Replay runs from ``start`` until the latest stored candle or user stop.
    Connect to ``ws_url`` for ``snapshot`` and ``tick_batch`` playback.

    Args:
        body: Symbol, timeframes, start anchor, indicators, optional autoplay.
        conn: Database connection.

    Returns:
        Session id and WebSocket path.
    """
    engine = _service().create_session(conn, body)
    return ReplaySessionResponse(
        session_id=engine.session_id,
        ws_url=f"/ws/replay/{engine.session_id}",
    )


@router.get("/sessions/{session_id}", response_model=ReplayStateResponse)
def get_replay_session(
    session_id: UUID,
    conn: psycopg.Connection = Depends(get_db),
) -> ReplayStateResponse:
    """
    Return current replay session state (cursor, queue depth, indicators).

    Does not advance playback; use WebSocket for stepping.

    Args:
        session_id: Session UUID.
        conn: Database connection.

    Returns:
        Session snapshot.
    """
    engine = _service().get_engine(conn, session_id)
    return _service().to_state_response(engine)


@router.delete("/sessions/{session_id}", status_code=204)
def delete_replay_session(
    session_id: UUID,
    conn: psycopg.Connection = Depends(get_db),
) -> None:
    """
    Tear down a replay session (database + in-memory cache).

    Args:
        session_id: Session UUID.
        conn: Database connection.
    """
    _service().delete_session(conn, session_id)
