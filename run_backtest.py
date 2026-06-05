#!/usr/bin/env python3
"""
Backtest entry point: load synced data, run configured strategy, and save outputs.

Orchestrates the vertical slice; business logic lives in the data, signal, and backtest modules.
"""

from __future__ import annotations

import logging
import sys
from datetime import UTC, datetime, timedelta

from backtest.engine import run_backtest
from backtest.metrics import compute_metrics, save_equity_curve
from config import load_config
from data.loader import get_candles
from data.storage import candle_count, run_migrations_on_startup
from exceptions import DataGapError
from signals.evaluator import evaluate_signals

DAYS_PER_YEAR = 365

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    """Configure root logging for CLI output."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )


def ensure_data(symbol: str) -> None:
    """
    Ensure the database schema exists and canonical 1m candles are already available.

    Args:
        symbol: Trading pair expected to have synced canonical candles.

    Side effects:
        Applies DB migrations.

    Raises:
        DataGapError: If canonical 1m candles for the symbol do not exist yet.
    """
    applied = run_migrations_on_startup()
    if applied:
        logger.info("Applied %s database migration(s)", applied)
    stored_count = candle_count(symbol, "1m")
    if stored_count == 0:
        raise DataGapError(
            f"No canonical 1m candles found for {symbol}. "
            "Run `python run_sync.py --backfill` first."
        )
    logger.info("Using synced canonical candles for %s (1m rows=%s).", symbol, f"{stored_count:,}")


def main() -> None:
    """Run the backtest pipeline end-to-end."""
    _configure_logging()
    app_config = load_config()

    ensure_data(app_config.symbol)

    end_date = datetime.now(UTC).date()
    # Backtest window matches the configured fetch depth, not the full DB history.
    start_date = end_date - timedelta(days=DAYS_PER_YEAR * app_config.years)
    candles = get_candles(
        app_config.symbol,
        app_config.timeframe,
        start_date.isoformat(),
        end_date.isoformat(),
    )
    if candles.empty:
        raise DataGapError(
            f"No candles for {app_config.symbol} {app_config.timeframe} "
            f"between {start_date} and {end_date}"
        )

    entry_signals, exit_signals = evaluate_signals(candles, app_config.strategy)
    trades, equity = run_backtest(
        candles,
        entry_signals,
        exit_signals,
        initial_capital=app_config.initial_capital,
    )
    metrics = compute_metrics(trades, equity)

    logger.info("--- Trades ---")
    for index, trade in enumerate(trades, 1):
        forced_flag = " [forced close]" if trade.forced_close else ""
        logger.info(
            "%3d. %s -> %s  %+.2f%%%s",
            index,
            trade.entry_date.date(),
            trade.exit_date.date(),
            trade.return_pct,
            forced_flag,
        )

    logger.info("--- Summary ---")
    logger.info("Trades:        %s", metrics["trade_count"])
    logger.info("Win rate:      %.1f%%", metrics["win_rate"] * 100)
    logger.info("Total return:  %.2f%%", metrics["total_return"] * 100)
    logger.info("Max drawdown:  %.2f%%", metrics["max_drawdown"] * 100)
    logger.info(
        "Capital:       $%s -> $%s",
        f"{metrics['initial_capital']:,.2f}",
        f"{metrics['final_capital']:,.2f}",
    )
    if metrics["forced_close"]:
        logger.info("Note: final position was closed at last bar close (no next bar).")

    equity_path = app_config.output_dir / app_config.equity_curve_filename
    saved_path = save_equity_curve(equity, candles, equity_path)
    logger.info("Equity curve saved to %s", saved_path.resolve())

    # Level-triggered: every bar where RSI crossed the threshold, not only trade entries.
    logger.info("--- Entry signal dates ---")
    entry_dates = candles.loc[entry_signals, "ts"]
    for timestamp in entry_dates:
        logger.info("  %s", timestamp.date())


if __name__ == "__main__":
    try:
        main()
    except DataGapError as error:
        logger.error("%s", error)
        sys.exit(1)
