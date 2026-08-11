#!/usr/bin/env python3
"""
Cron-friendly screener CLI (Phase 8).

Example:
  python run_scan.py --once --timeframes 1h,1d \\
    --start 2024-01-01 --end 2024-06-01 --condition-file scan.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

from data.storage import connect, run_migrations_on_startup
from screener.pipeline import run_scan

logger = logging.getLogger("run_scan")


def _configure_logging() -> None:
    """Configure root logging for CLI / cron output."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def _parse_csv(value: str) -> list[str]:
    """Split a comma-separated list, stripping whitespace."""
    return [part.strip() for part in value.split(",") if part.strip()]


def _load_condition(path: Path) -> dict[str, Any]:
    """Load a JSON condition tree from disk."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Condition file must contain a JSON object")
    # Allow either a bare condition or {"condition": {...}}.
    if "condition" in payload and isinstance(payload["condition"], dict):
        return payload["condition"]
    return payload


def _default_symbols(conn: Any) -> list[str]:
    """List active symbols from the catalog."""
    from api.repositories.symbol_repository import SymbolRepository

    rows = SymbolRepository().list_symbols(conn, active_only=True)
    return [row.symbol for row in rows]


def _persist_result(
    conn: Any,
    *,
    symbols: list[str],
    timeframes: list[str],
    start: str,
    end: str,
    condition: dict[str, Any],
    alert_trigger: str,
    result: Any,
) -> str:
    """Insert a scan_runs row; returns scan_id string."""
    from datetime import UTC, datetime

    from api.repositories.scan_repository import ScanRepository

    start_ts = int(datetime.fromisoformat(start).replace(tzinfo=UTC).timestamp())
    # Inclusive end date → end of UTC day for storage.
    end_dt = datetime.fromisoformat(end).replace(tzinfo=UTC)
    end_ts = int(end_dt.timestamp())
    scan_id = uuid4()
    matches = [
        {
            "symbol": m.symbol,
            "timeframe": m.timeframe,
            "bar_ts": m.bar_ts,
            "triggered": m.triggered,
            "close": m.close,
        }
        for m in result.matches
    ]
    ScanRepository().insert(
        conn,
        scan_id=scan_id,
        timeframes=timeframes,
        symbols=symbols,
        start_ts=start_ts,
        end_ts=end_ts,
        condition_config=condition,
        alert_trigger=alert_trigger,
        matches=matches,
        alert_count=result.alert_count,
        duration_ms=result.duration_ms,
        status="completed",
        error_message=None,
    )
    return str(scan_id)


def main(argv: list[str] | None = None) -> int:
    """Run one screener pass and exit (cron-friendly)."""
    _configure_logging()
    parser = argparse.ArgumentParser(description="Run a multi-symbol screener scan")
    parser.add_argument(
        "--once",
        action="store_true",
        required=True,
        help="Run a single scan and exit (required for cron)",
    )
    parser.add_argument(
        "--timeframes",
        required=True,
        help="Comma-separated timeframes, e.g. 1h,1d",
    )
    parser.add_argument("--start", required=True, help="Inclusive ISO start date")
    parser.add_argument("--end", required=True, help="Inclusive ISO end date")
    parser.add_argument(
        "--condition-file",
        required=True,
        type=Path,
        help="JSON file with a condition tree",
    )
    parser.add_argument(
        "--symbols",
        default="",
        help="Optional comma-separated symbols (default: active catalog)",
    )
    parser.add_argument(
        "--alert-trigger",
        choices=("edge", "level"),
        default="edge",
        help="Alert trigger mode (default: edge)",
    )
    parser.add_argument(
        "--no-persist",
        action="store_true",
        help="Skip writing app.scan_runs",
    )
    args = parser.parse_args(argv)

    timeframes = _parse_csv(args.timeframes)
    if len(timeframes) < 1:
        logger.error("At least one timeframe is required")
        return 2

    condition = _load_condition(args.condition_file)
    applied = run_migrations_on_startup()
    if applied:
        logger.info("Applied %s database migration(s)", applied)

    with connect() as conn:
        symbols = _parse_csv(args.symbols) if args.symbols else _default_symbols(conn)
        if not symbols:
            logger.error("No symbols to scan")
            return 2

        result = run_scan(
            symbols=symbols,
            timeframes=timeframes,
            start=args.start,
            end=args.end,
            condition=condition,
            alert_trigger=args.alert_trigger,
        )

        scan_id = None
        if not args.no_persist:
            scan_id = _persist_result(
                conn,
                symbols=symbols,
                timeframes=timeframes,
                start=args.start,
                end=args.end,
                condition=condition,
                alert_trigger=args.alert_trigger,
                result=result,
            )
            conn.commit()

    logger.info(
        "Scan complete: matches=%s alerts=%s pairs=%s duration_ms=%s scan_id=%s errors=%s",
        len(result.matches),
        result.alert_count,
        result.scanned_pairs,
        result.duration_ms,
        scan_id,
        len(result.errors),
    )
    for err in result.errors:
        logger.warning(
            "Pair error %s %s: %s",
            err.get("symbol"),
            err.get("timeframe"),
            err.get("error"),
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
