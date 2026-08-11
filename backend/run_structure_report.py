#!/usr/bin/env python3
"""
Export market structure swings for manual chart review (D-60).

Loads candles from TimescaleDB, runs the structure pipeline, and writes CSV/JSON
under ``output/``.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import pandas as pd

from data.storage import candle_count, run_migrations_on_startup
from exceptions import DataGapError
from structure import StructureContext, analyze_structure
from structure.types import Trend

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    """Configure root logging for CLI output."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def _ensure_data(symbol: str) -> None:
    """Ensure schema exists and canonical candles are present."""
    applied = run_migrations_on_startup()
    if applied:
        logger.info("Applied %s database migration(s)", applied)
    stored = candle_count(symbol, "1m")
    if stored == 0:
        raise DataGapError(
            f"No canonical 1m candles found for {symbol}. "
            "Run `python run_sync.py --backfill` first."
        )


def _swings_frame(result_swings: list) -> pd.DataFrame:
    """Convert swing points to a flat DataFrame for CSV export."""
    rows = [
        {
            "ts": s.ts.isoformat(),
            "index": s.index,
            "price": s.price,
            "kind": s.kind.value,
            "label": s.label.value,
            "confirmed": s.confirmed,
            "confirmation_index": s.confirmation_index,
        }
        for s in result_swings
    ]
    return pd.DataFrame(rows)


def _trend_counts(trend: pd.Series) -> dict[str, int]:
    """Count trend state occurrences."""
    counts: dict[str, int] = {}
    for value in trend:
        key = value.value if isinstance(value, Trend) else str(value)
        counts[key] = counts.get(key, 0) + 1
    return counts


def main(argv: list[str] | None = None) -> int:
    """Run structure report export."""
    _configure_logging()
    parser = argparse.ArgumentParser(description="Export structure swings for chart review")
    parser.add_argument("--symbol", default="BTC/USDT")
    parser.add_argument("--timeframe", default="1h")
    parser.add_argument("--start", required=True, help="Inclusive ISO start date")
    parser.add_argument("--end", required=True, help="Inclusive ISO end date")
    parser.add_argument(
        "--htf",
        action="append",
        default=[],
        help="Higher timeframe (repeatable). Default: 4h and 1d when omitted.",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    parser.add_argument(
        "--confirmed-only",
        action="store_true",
        help="Export confirmed swings only",
    )
    args = parser.parse_args(argv)

    _ensure_data(args.symbol)
    htf = args.htf if args.htf else ["4h", "1d"]
    args.output_dir.mkdir(parents=True, exist_ok=True)

    safe_symbol = args.symbol.replace("/", "_")
    if htf:
        ctx = StructureContext.load(
            args.symbol,
            args.timeframe,
            htf,
            args.start,
            args.end,
            confirmed_only=args.confirmed_only,
        )
        result = ctx.base
        summary = {
            "symbol": args.symbol,
            "base_tf": args.timeframe,
            "htf": list(htf),
            "levels": {
                "support": result.levels.support,
                "resistance": result.levels.resistance,
            },
            "trend_counts": _trend_counts(result.trend),
            "htf_trend_counts": {
                tf: _trend_counts(series) for tf, series in ctx.htf_trend_on_base.items()
            },
            "swing_count": len(result.swings),
        }
    else:
        from data.loader import get_candles

        candles = get_candles(args.symbol, args.timeframe, args.start, args.end)
        if candles.empty:
            raise DataGapError("No candles in requested range")
        result = analyze_structure(candles, confirmed_only=args.confirmed_only)
        summary = {
            "symbol": args.symbol,
            "base_tf": args.timeframe,
            "htf": [],
            "levels": {
                "support": result.levels.support,
                "resistance": result.levels.resistance,
            },
            "trend_counts": _trend_counts(result.trend),
            "swing_count": len(result.swings),
        }

    csv_path = args.output_dir / f"structure_{safe_symbol}_{args.timeframe}_swings.csv"
    json_path = args.output_dir / f"structure_{safe_symbol}_{args.timeframe}_summary.json"
    _swings_frame(result.swings).to_csv(csv_path, index=False)
    json_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    logger.info("Wrote %s (%s swings)", csv_path, len(result.swings))
    logger.info("Wrote %s", json_path)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (DataGapError, ValueError) as exc:
        logging.error("%s", exc)
        raise SystemExit(1) from exc
