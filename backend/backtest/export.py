"""
Trade log CSV export (D-44).
"""

from __future__ import annotations

import csv
from pathlib import Path

from backtest.engine import Trade

TRADE_CSV_COLUMNS = (
    "entry_date",
    "exit_date",
    "side",
    "entry_price",
    "exit_price",
    "return_pct",
    "exit_reason",
    "forced_close",
    "size",
    "commission_paid",
    "pnl_quote",
)


def _trade_row(trade: Trade) -> dict[str, str | float | bool]:
    """Map a Trade to a CSV row dict with stable column names."""
    return {
        "entry_date": trade.entry_date.isoformat(),
        "exit_date": trade.exit_date.isoformat(),
        "side": trade.side,
        "entry_price": trade.entry_price,
        "exit_price": trade.exit_price,
        "return_pct": trade.return_pct,
        "exit_reason": trade.exit_reason,
        "forced_close": trade.forced_close,
        "size": trade.size,
        "commission_paid": trade.commission_paid,
        "pnl_quote": trade.pnl_quote,
    }


def export_trades_csv(trades: list[Trade], path: str | Path) -> Path:
    """
    Write closed trades to a CSV file.

    Args:
        trades: Completed trades from the backtest engine.
        path: Output file path.

    Returns:
        Resolved path to the written CSV.

    Side effects:
        Creates parent directories and writes the CSV file.
    """
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=TRADE_CSV_COLUMNS)
        writer.writeheader()
        for trade in trades:
            writer.writerow(_trade_row(trade))

    return output_path.resolve()
