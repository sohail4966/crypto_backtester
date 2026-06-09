"""
Replay session REST endpoints.
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
    return get_replay_service()


@router.post("/sessions", response_model=ReplaySessionResponse, status_code=201)
def create_replay_session(
    body: ReplaySessionCreate,
    conn: psycopg.Connection = Depends(get_db),
) -> ReplaySessionResponse:
    """Create an in-memory bar replay session."""
    session = _service().create_session(conn, body)
    return ReplaySessionResponse(
        session_id=session.session_id,
        ws_url=f"/ws/replay/{session.session_id}",
    )


@router.get("/sessions/{session_id}", response_model=ReplayStateResponse)
def get_replay_session(session_id: UUID) -> ReplayStateResponse:
    """Return replay session state snapshot."""
    session = _service().get_session(session_id)
    return _service().to_state_response(session)


@router.delete("/sessions/{session_id}", status_code=204)
def delete_replay_session(session_id: UUID) -> None:
    """Tear down a replay session."""
    _service().delete_session(session_id)
