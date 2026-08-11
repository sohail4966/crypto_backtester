"""
Screener HTTP orchestration (Phase 8).
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import psycopg

from api.exceptions import ValidationError
from api.repositories.scan_repository import ScanRepository
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


def _unix_to_iso_date(ts: int) -> str:
    """Convert unix seconds to a UTC ISO date string for ``get_candles``."""
    return datetime.fromtimestamp(ts, tz=UTC).date().isoformat()


class ScanService:
    """Business logic for ``POST /scan``."""

    def __init__(
        self,
        scan_repository: ScanRepository | None = None,
        symbol_repository: SymbolRepository | None = None,
    ) -> None:
        self._scans = scan_repository or ScanRepository()
        self._symbols = symbol_repository or SymbolRepository()

    def run(self, conn: psycopg.Connection, body: ScanCreateRequest) -> ScanRunResponse:
        """
        Execute a synchronous multi-symbol scan and optionally persist results.
        """
        for tf in body.timeframes:
            try:
                validate_timeframe(tf)
            except ValueError as exc:
                raise ValidationError("INVALID_TIMEFRAME", str(exc)) from exc

        if body.symbols:
            symbols = list(body.symbols)
        else:
            rows = self._symbols.list_symbols(conn, active_only=True)
            symbols = [row.symbol for row in rows]
        if not symbols:
            raise ValidationError("NO_SYMBOLS", "No symbols available to scan")

        start = _unix_to_iso_date(body.start)
        end = _unix_to_iso_date(body.end)

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
        if body.persist:
            scan_id = uuid4()
            self._scans.insert(
                conn,
                scan_id=scan_id,
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
            )
            persisted = True

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
        )
