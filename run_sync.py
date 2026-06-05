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
from data.sync import sync_all

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
    return parser.parse_args()


def main() -> int:
    """
    Execute one sync pass and return a process exit code.

    Returns:
        0 when all symbols sync successfully, otherwise 1.
    """
    _configure_logging()
    args = parse_args()
    if not args.once:
        logger.error("Only --once mode is currently supported. Run: python run_sync.py --once")
        return 2

    applied = run_migrations_on_startup()
    if applied:
        logger.info("Applied %s database migration(s)", applied)

    config = load_data_config()
    results = sync_all(config)
    failed = [result for result in results if result.status != "ok"]

    logger.info("Sync summary: %s total, %s failed", len(results), len(failed))
    if failed:
        for result in failed:
            logger.error("  %s %s failed: %s", result.symbol, result.timeframe, result.error)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
