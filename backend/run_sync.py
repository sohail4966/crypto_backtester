#!/usr/bin/env python3
"""
Sync entry point for Phase 1 data ingestion.

Runs one sync pass across all configured symbols so cron can call it hourly.
"""

from __future__ import annotations

import argparse
import logging
import sys

from data.config import load_data_config
from data.storage import run_migrations_on_startup
from data.sync import SyncResult, sync_all

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    """Configure root logging for CLI output."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def parse_args() -> argparse.Namespace:
    """
    Parse CLI arguments for run_sync.

    Returns:
        Parsed argparse namespace.
    """
    parser = argparse.ArgumentParser(
        description="Sync configured symbols into canonical 1m storage."
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one sync pass and exit (intended for cron).",
    )
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Run one full backfill-oriented pass across all configured symbols.",
    )
    return parser.parse_args()


def _log_progress(completed: int, total: int, result: SyncResult) -> None:
    """
    Log a compact completion line for each finished symbol.

    Args:
        completed: Number of symbols completed so far.
        total: Total symbols in this run.
        result: Per-symbol sync result.
    """
    if result.status == "ok":
        logger.info(
            "[%s/%s] %s %s - %s rows inserted",
            completed,
            total,
            result.symbol,
            result.timeframe,
            result.inserted,
        )
        return
    logger.error(
        "[%s/%s] %s %s failed: %s",
        completed,
        total,
        result.symbol,
        result.timeframe,
        result.error,
    )


def _run_single_pass(mode: str) -> int:
    """
    Execute one sync pass for either cron mode or backfill mode.

    Args:
        mode: Either "once" or "backfill", used for logging context.

    Returns:
        0 when all symbols sync successfully, otherwise 1.
    """
    logger.info("Starting sync mode: %s", mode)
    applied = run_migrations_on_startup()
    if applied:
        logger.info("Applied %s database migration(s)", applied)

    config = load_data_config()
    results = sync_all(config, progress_callback=_log_progress)
    failed = [result for result in results if result.status != "ok"]

    logger.info("Sync summary: %s total, %s failed", len(results), len(failed))
    if failed:
        for result in failed:
            logger.error("  %s %s failed: %s", result.symbol, result.timeframe, result.error)
        return 1
    return 0


def main() -> int:
    """
    Execute one sync/backfill pass and return a process exit code.

    Returns:
        0 when all symbols sync successfully, otherwise 1.
    """
    _configure_logging()
    args = parse_args()
    selected = int(args.once) + int(args.backfill)
    if selected != 1:
        logger.error("Specify exactly one mode: --once or --backfill")
        return 2
    if args.once:
        return _run_single_pass("once")
    return _run_single_pass("backfill")


if __name__ == "__main__":
    sys.exit(main())
