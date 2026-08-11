"""
Repository for ``app.backtest_runs`` persistence.
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
class BacktestRunRow:
    """One row from ``app.backtest_runs``."""

    run_id: UUID
    symbol: str
    timeframe: str
    start_ts: int
    end_ts: int
    initial_capital: float
    strategy_name: str | None
    strategy_config: dict[str, Any]
    backtest_config: dict[str, Any]
    metrics: dict[str, Any]
    trades: list[dict[str, Any]]
    signals: list[dict[str, Any]]
    equity: list[dict[str, Any]]
    status: str
    error_message: str | None
    user_id: UUID | None
    created_at: datetime


def _row_to_run(row: tuple[Any, ...]) -> BacktestRunRow:
    """Map a SELECT/RETURNING tuple to ``BacktestRunRow``."""
    return BacktestRunRow(
        run_id=row[0],
        symbol=row[1],
        timeframe=row[2],
        start_ts=int(row[3]),
        end_ts=int(row[4]),
        initial_capital=float(row[5]),
        strategy_name=row[6],
        strategy_config=dict(_maybe_json(row[7]) or {}),
        backtest_config=dict(_maybe_json(row[8]) or {}),
        metrics=dict(_maybe_json(row[9]) or {}),
        trades=list(_maybe_json(row[10]) or []),
        signals=list(_maybe_json(row[11]) or []),
        equity=list(_maybe_json(row[12]) or []),
        status=str(row[13]),
        error_message=row[14],
        user_id=row[15],
        created_at=row[16],
    )


class BacktestRepository:
    """Insert and fetch persisted backtest runs."""

    def insert(
        self,
        conn: psycopg.Connection,
        *,
        run_id: UUID,
        symbol: str,
        timeframe: str,
        start_ts: int,
        end_ts: int,
        initial_capital: float,
        strategy_name: str | None,
        strategy_config: dict[str, Any],
        backtest_config: dict[str, Any],
        metrics: dict[str, Any],
        trades: list[dict[str, Any]],
        signals: list[dict[str, Any]],
        equity: list[dict[str, Any]],
        status: str = "completed",
        error_message: str | None = None,
        user_id: UUID | None = None,
    ) -> BacktestRunRow:
        """
        Persist a completed backtest run.

        Raises:
            RuntimeError: When INSERT returns no row.
        """
        with conn.cursor() as cur:
            cur.execute(
                queries.INSERT_BACKTEST_RUN,
                (
                    run_id,
                    symbol,
                    timeframe,
                    start_ts,
                    end_ts,
                    initial_capital,
                    strategy_name,
                    _json_dump(strategy_config),
                    _json_dump(backtest_config),
                    _json_dump(metrics),
                    _json_dump(trades),
                    _json_dump(signals),
                    _json_dump(equity),
                    status,
                    error_message,
                    user_id,
                ),
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("INSERT backtest run returned no row")
            conn.commit()
            return _row_to_run(row)

    def get(self, conn: psycopg.Connection, run_id: UUID) -> BacktestRunRow | None:
        """Fetch one run by id, or ``None`` when missing."""
        with conn.cursor() as cur:
            cur.execute(queries.SELECT_BACKTEST_RUN, (run_id,))
            row = cur.fetchone()
            if row is None:
                return None
            return _row_to_run(row)
