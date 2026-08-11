"""
Screener HTTP endpoints (Phase 8).
"""

from __future__ import annotations

from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends
from pydantic import ValidationError as PydanticValidationError

from api.deps import get_current_user, get_db
from api.exceptions import ValidationError
from api.repositories.user_repository import UserRow
from api.schemas.scan import ScanCreateRequest, ScanRunResponse
from api.services.scan_service import ScanService

router = APIRouter(prefix="/scan", tags=["scan"])
_service = ScanService()


@router.post("", response_model=ScanRunResponse, status_code=201)
def create_scan(
    body: ScanCreateRequest,
    conn: psycopg.Connection = Depends(get_db),
    current: UserRow = Depends(get_current_user),
) -> ScanRunResponse:
    """
    Run a multi-symbol / multi-TF scan synchronously.

    Defaults to active catalog symbols when ``symbols`` is omitted.
    Persists to ``app.scan_runs`` when ``persist`` is true (default).
    Requires JWT (BE-004); attribution uses the token subject (G-004).
    """
    try:
        return _service.run(conn, body, user_id=current.id)
    except PydanticValidationError as exc:
        raise ValidationError("INVALID_SCAN", str(exc)) from exc


@router.get("/{scan_id}", response_model=ScanRunResponse)
def get_scan(
    scan_id: UUID,
    conn: psycopg.Connection = Depends(get_db),
    current: UserRow = Depends(get_current_user),
) -> ScanRunResponse:
    """Retrieve a persisted scan run owned by the caller (G-004)."""
    return _service.get(conn, scan_id, user_id=current.id)
