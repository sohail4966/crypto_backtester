"""
Repository for ``app.scan_runs`` persistence.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

import psycopg

from api.repositories import queries


def _json_dump(value: Any) -> str:
    """Serialize a Python object for a JSONB bind parameter."""
    return json.dumps(value, default=str)


def _maybe_json(value: Any) -> Any:
    """Decode JSON text from drivers that return str for JSONB."""
    if isinstance(value, str):
        return json.loads(value)
    return value


@dataclass
class ScanRunRow:
    """One row from ``app.scan_runs``."""

    scan_id: UUID
    timeframes: list[str]
    symbols: list[str]
    start_ts: int
    end_ts: int
    condition_config: dict[str, Any]
    alert_trigger: str
    matches: list[dict[str, Any]]
    alert_count: int
    duration_ms: int
    status: str
    error_message: str | None
    created_at: datetime


def _row_to_scan(row: tuple[Any, ...]) -> ScanRunRow:
    """Map a SELECT/RETURNING tuple to ``ScanRunRow``."""
    return ScanRunRow(
        scan_id=row[0],
        timeframes=list(row[1] or []),
        symbols=list(row[2] or []),
        start_ts=int(row[3]),
        end_ts=int(row[4]),
        condition_config=dict(_maybe_json(row[5]) or {}),
        alert_trigger=str(row[6]),
        matches=list(_maybe_json(row[7]) or []),
        alert_count=int(row[8]),
        duration_ms=int(row[9]),
        status=str(row[10]),
        error_message=row[11],
        created_at=row[12],
    )


class ScanRepository:
    """Insert and fetch persisted scan runs."""

    def insert(
        self,
        conn: psycopg.Connection,
        *,
        scan_id: UUID,
        timeframes: list[str],
        symbols: list[str],
        start_ts: int,
        end_ts: int,
        condition_config: dict[str, Any],
        alert_trigger: str,
        matches: list[dict[str, Any]],
        alert_count: int,
        duration_ms: int,
        status: str = "completed",
        error_message: str | None = None,
    ) -> ScanRunRow:
        """Insert a completed scan run and return the row."""
        with conn.cursor() as cur:
            cur.execute(
                queries.INSERT_SCAN_RUN,
                (
                    scan_id,
                    timeframes,
                    symbols,
                    start_ts,
                    end_ts,
                    _json_dump(condition_config),
                    alert_trigger,
                    _json_dump(matches),
                    alert_count,
                    duration_ms,
                    status,
                    error_message,
                ),
            )
            row = cur.fetchone()
        if row is None:
            raise RuntimeError("INSERT scan_runs returned no row")
        return _row_to_scan(row)

    def get(self, conn: psycopg.Connection, scan_id: UUID) -> ScanRunRow | None:
        """Fetch one scan run by id."""
        with conn.cursor() as cur:
            cur.execute(queries.SELECT_SCAN_RUN, (scan_id,))
            row = cur.fetchone()
        if row is None:
            return None
        return _row_to_scan(row)
