"""
Backtest HTTP endpoints (Phase 4d).
"""

from __future__ import annotations

from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends
from pydantic import ValidationError as PydanticValidationError

from api.deps import get_current_user, get_db
from api.exceptions import ValidationError
from api.repositories.user_repository import UserRow
from api.schemas.backtest import (
    BacktestCreateRequest,
    BacktestRunResponse,
    BacktestTradesResponse,
    StrategiesResponse,
)
from api.services.backtest_service import BacktestService

router = APIRouter(prefix="/backtest", tags=["backtest"])
_service = BacktestService()


@router.get("/strategies", response_model=StrategiesResponse)
def list_strategies() -> StrategiesResponse:
    """List named strategies from server ``config.yaml``."""
    return _service.list_strategies()


@router.post("", response_model=BacktestRunResponse, status_code=201)
def create_backtest(
    body: BacktestCreateRequest,
    conn: psycopg.Connection = Depends(get_db),
    current: UserRow = Depends(get_current_user),
) -> BacktestRunResponse:
    """
    Run a backtest synchronously and persist the result.

    Provide exactly one of ``strategy_name`` (catalog) or inline ``strategy``.
    Requires JWT; attribution uses the token subject (BE-004 / BE-005).
    """
    try:
        return _service.run(conn, body, user_id=current.id)
    except PydanticValidationError as exc:
        raise ValidationError("INVALID_STRATEGY", str(exc)) from exc


@router.get("/{run_id}", response_model=BacktestRunResponse)
def get_backtest(
    run_id: UUID,
    conn: psycopg.Connection = Depends(get_db),
    current: UserRow = Depends(get_current_user),
) -> BacktestRunResponse:
    """Return a persisted backtest run summary (owner only; G-004)."""
    return _service.get_run(conn, run_id, user_id=current.id)


@router.get("/{run_id}/trades", response_model=BacktestTradesResponse)
def get_backtest_trades(
    run_id: UUID,
    conn: psycopg.Connection = Depends(get_db),
    current: UserRow = Depends(get_current_user),
) -> BacktestTradesResponse:
    """Return the full round-trip trade log for a run (owner only; G-004)."""
    return _service.get_trades(conn, run_id, user_id=current.id)
