"""
Replay session REST endpoints.
"""

from __future__ import annotations

from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Query

from api.deps import get_db
from api.schemas.chart_data import ChartDataResponse, ReplayRunCreate, ReplayRunResponse, ReplayTradesResponse
from api.schemas.replay import ReplaySessionCreate, ReplaySessionResponse, ReplayStateResponse
from api.services.replay_service import ReplayService, get_replay_service

router = APIRouter(prefix="/replay", tags=["replay"])


def _service() -> ReplayService:
    return get_replay_service()


@router.post("/runs", response_model=ReplayRunResponse, status_code=201, response_model_by_alias=True)
def create_replay_run(
    body: ReplayRunCreate,
    conn: psycopg.Connection = Depends(get_db),
) -> ReplayRunResponse:
    """Create an in-memory replay run for REST chunk buffering."""
    session = _service().create_run(conn, body)
    return ReplayRunResponse(
        run_id=str(session.session_id),
        symbol_id=session.symbol,
        timeframe=session.timeframe,
        start=session.start,
        end=session.end,
        total_bars=len(session.bars),
    )


@router.get("/{run_id}/chunk", response_model=ChartDataResponse, response_model_by_alias=True)
def get_replay_chunk(
    run_id: UUID,
    from_ts: int = Query(alias="from"),
    limit: int | None = Query(default=None),
    conn: psycopg.Connection = Depends(get_db),
) -> ChartDataResponse:
    """Return a chart-data chunk from a replay run."""
    return _service().get_chunk(conn, run_id, from_ts, limit=limit)


@router.get("/{run_id}/trades", response_model=ReplayTradesResponse, response_model_by_alias=True)
def get_replay_trades(run_id: UUID) -> ReplayTradesResponse:
    """Return trades for a replay run (empty until Phase 4c)."""
    _service().get_session(run_id)
    return ReplayTradesResponse(run_id=str(run_id), trades=[])


@router.delete("/{run_id}", status_code=204)
def delete_replay_run(run_id: UUID) -> None:
    """Tear down a replay run."""
    _service().delete_session(run_id)


@router.post("/sessions", response_model=ReplaySessionResponse, status_code=201)
def create_replay_session(
    body: ReplaySessionCreate,
    conn: psycopg.Connection = Depends(get_db),
) -> ReplaySessionResponse:
    """Create an in-memory bar replay session (WebSocket control plane)."""
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
