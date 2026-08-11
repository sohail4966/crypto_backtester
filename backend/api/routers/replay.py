"""
Replay session REST endpoints (Phase 4c).

Open-ended sessions: create via POST, control playback over WebSocket v2.
"""

from __future__ import annotations

from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends

from api.deps import get_current_user, get_db
from api.repositories.user_repository import UserRow
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
    current: UserRow = Depends(get_current_user),
) -> ReplaySessionResponse:
    """
    Create an open-ended bar replay session owned by the JWT subject.

    Replay runs from ``start`` until the latest stored candle or user stop.
    Connect to ``ws_url`` with ``?token=`` for ``snapshot`` and ``tick_batch``.
    """
    engine = _service().create_session(conn, body, user_id=current.id)
    return ReplaySessionResponse(
        session_id=engine.session_id,
        ws_url=f"/ws/replay/{engine.session_id}",
    )


@router.get("/sessions/{session_id}", response_model=ReplayStateResponse)
def get_replay_session(
    session_id: UUID,
    conn: psycopg.Connection = Depends(get_db),
    current: UserRow = Depends(get_current_user),
) -> ReplayStateResponse:
    """Return current replay session state (owner only)."""
    engine = _service().get_engine(conn, session_id, user_id=current.id)
    return _service().to_state_response(engine)


@router.delete("/sessions/{session_id}", status_code=204)
def delete_replay_session(
    session_id: UUID,
    conn: psycopg.Connection = Depends(get_db),
    current: UserRow = Depends(get_current_user),
) -> None:
    """Tear down a replay session (owner only)."""
    _service().delete_session(conn, session_id, user_id=current.id)
