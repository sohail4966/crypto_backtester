"""
Screener HTTP orchestration (Phase 8).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

import psycopg

from api import settings
from api.exceptions import NotFoundError, ValidationError

logger = logging.getLogger(__name__)
from api.repositories.scan_repository import ScanRepository, ScanRunRow
from api.repositories.symbol_repository import SymbolRepository
from api.schemas.scan import (
    ScanCreateRequest,
    ScanErrorResponse,
    ScanMatchResponse,
    ScanRunResponse,
)
from api.services.timeframes import validate_timeframe
from data.loader import get_candles
from exceptions import InvalidSignalError
from screener.pipeline import run_scan


def _unix_to_iso(ts: int) -> str:
    """Convert unix seconds to a full UTC ISO timestamptz string for ``get_candles``."""
    return datetime.fromtimestamp(ts, tz=UTC).isoformat()


class ScanService:
    """Business logic for ``POST /scan`` and ``GET /scan/{id}``."""

    def __init__(
        self,
        scan_repository: ScanRepository | None = None,
        symbol_repository: SymbolRepository | None = None,
    ) -> None:
        self._scans = scan_repository or ScanRepository()
        self._symbols = symbol_repository or SymbolRepository()

    def _row_to_response(self, row: ScanRunRow) -> ScanRunResponse:
        """Map a persisted scan row to the HTTP response shape."""
        matches = [ScanMatchResponse.model_validate(m) for m in row.matches]
        return ScanRunResponse(
            scan_id=row.scan_id,
            timeframes=row.timeframes,
            symbols=row.symbols,
            start=row.start_ts,
            end=row.end_ts,
            alert_trigger=row.alert_trigger,  # type: ignore[arg-type]
            matches=matches,
            alert_count=row.alert_count,
            duration_ms=row.duration_ms,
            scanned_pairs=len(row.timeframes) * len(row.symbols),
            errors=[],
            persisted=True,
        )

    def get(
        self,
        conn: psycopg.Connection,
        scan_id: UUID,
        *,
        user_id: UUID,
    ) -> ScanRunResponse:
        """Fetch a persisted scan run owned by ``user_id`` (G-004)."""
        row = self._scans.get(conn, scan_id)
        if row is None or row.user_id != user_id:
            raise NotFoundError("SCAN_NOT_FOUND", f"Scan {scan_id} not found")
        return self._row_to_response(row)

    def run(
        self,
        conn: psycopg.Connection,
        body: ScanCreateRequest,
        *,
        user_id: UUID,
    ) -> ScanRunResponse:
        """
        Execute a synchronous multi-symbol scan and optionally persist results.
        """
        for tf in body.timeframes:
            try:
                validate_timeframe(tf)
            except ValueError as exc:
                raise ValidationError("INVALID_TIMEFRAME", str(exc)) from exc

        window_sec = body.end - body.start
        max_window = settings.backtest_max_window_sec()
        if window_sec > max_window:
            raise ValidationError(
                "WINDOW_TOO_LARGE",
                f"Scan window must be <= {max_window} seconds",
            )

        if body.symbols:
            symbols = list(body.symbols)
        else:
            rows = self._symbols.list_symbols(conn, active_only=True)
            symbols = [row.symbol for row in rows]
        if not symbols:
            raise ValidationError("NO_SYMBOLS", "No symbols available to scan")

        max_symbols = settings.scan_max_symbols()
        if len(symbols) > max_symbols:
            raise ValidationError(
                "TOO_MANY_SYMBOLS",
                f"Scan allows at most {max_symbols} symbols",
            )

        start = _unix_to_iso(body.start)
        end = _unix_to_iso(body.end)

        try:
            result = run_scan(
                symbols=symbols,
                timeframes=body.timeframes,
                start=start,
                end=end,
                condition=body.condition,
                alert_trigger=body.alert_trigger,
                loader=get_candles,
            )
        except InvalidSignalError as exc:
            raise ValidationError("INVALID_CONDITION", str(exc)) from exc

        matches = [
            ScanMatchResponse(
                symbol=m.symbol,
                timeframe=m.timeframe,
                bar_ts=m.bar_ts,
                triggered=m.triggered,
                close=m.close,
            )
            for m in result.matches
        ]
        errors = [
            ScanErrorResponse(
                symbol=err["symbol"],
                timeframe=err["timeframe"],
                error=err["error"],
            )
            for err in result.errors
        ]

        scan_id = None
        persisted = False
        persist_error: str | None = None
        if body.persist:
            candidate_id = uuid4()
            try:
                self._scans.insert(
                    conn,
                    scan_id=candidate_id,
                    timeframes=body.timeframes,
                    symbols=symbols,
                    start_ts=body.start,
                    end_ts=body.end,
                    condition_config=body.condition,
                    alert_trigger=body.alert_trigger,
                    matches=[m.model_dump() for m in matches],
                    alert_count=result.alert_count,
                    duration_ms=result.duration_ms,
                    status="completed",
                    user_id=user_id,
                )
                scan_id = candidate_id
                persisted = True
            except Exception:
                # Honest persistence flag (BE-001) — still return compute
                # results, but surface the failure in logs + envelope so ops
                # can distinguish infra failure from ``persist=False``
                # (BE-L2-014).
                logger.exception(
                    "Scan persist failed for candidate_id=%s", candidate_id
                )
                scan_id = None
                persisted = False
                persist_error = "PERSIST_FAILED"

        return ScanRunResponse(
            scan_id=scan_id,
            timeframes=body.timeframes,
            symbols=symbols,
            start=body.start,
            end=body.end,
            alert_trigger=body.alert_trigger,
            matches=matches,
            alert_count=result.alert_count,
            duration_ms=result.duration_ms,
            scanned_pairs=result.scanned_pairs,
            errors=errors,
            persisted=persisted,
            persist_error=persist_error,
        )
