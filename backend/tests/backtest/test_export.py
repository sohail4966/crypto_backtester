"""
Tests for backtest.export (D-44).
"""

import csv
from pathlib import Path

import pandas as pd
import pytest

from backtest.engine import Trade
from backtest.export import TRADE_CSV_COLUMNS, export_trades_csv


def _sample_trades() -> list[Trade]:
    """Two trades covering long/short and forced close."""
    return [
        Trade(
            entry_date=pd.Timestamp("2024-01-01", tz="UTC"),
            exit_date=pd.Timestamp("2024-01-10", tz="UTC"),
            entry_price=100.0,
            exit_price=110.0,
            return_pct=10.0,
            side="long",
            exit_reason="signal",
            forced_close=False,
            size=1000.0,
            commission_paid=2.0,
            pnl_quote=98.0,
        ),
        Trade(
            entry_date=pd.Timestamp("2024-02-01", tz="UTC"),
            exit_date=pd.Timestamp("2024-02-05", tz="UTC"),
            entry_price=200.0,
            exit_price=190.0,
            return_pct=5.263157894736842,
            side="short",
            exit_reason="stop_loss",
            forced_close=True,
            size=500.0,
            commission_paid=1.5,
            pnl_quote=23.5,
        ),
    ]


def test_export_trades_csv_row_count_matches_trades(tmp_path: Path) -> None:
    """CSV has one data row per trade plus a header."""
    trades = _sample_trades()
    output = tmp_path / "trades.csv"

    export_trades_csv(trades, output)

    with output.open(encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    assert len(rows) == len(trades) + 1


def test_export_trades_csv_columns_and_values(tmp_path: Path) -> None:
    """CSV columns match D-44 and preserve trade field values."""
    trades = _sample_trades()
    output = tmp_path / "nested" / "trades.csv"

    export_trades_csv(trades, output)

    with output.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == list(TRADE_CSV_COLUMNS)
        rows = list(reader)

    assert len(rows) == 2
    assert rows[0]["side"] == "long"
    assert rows[0]["exit_reason"] == "signal"
    assert rows[0]["forced_close"] == "False"
    assert float(rows[0]["entry_price"]) == pytest.approx(100.0)
    assert float(rows[0]["pnl_quote"]) == pytest.approx(98.0)

    assert rows[1]["side"] == "short"
    assert rows[1]["exit_reason"] == "stop_loss"
    assert rows[1]["forced_close"] == "True"
    assert float(rows[1]["return_pct"]) == pytest.approx(5.263157894736842)


def test_export_trades_csv_empty_trade_list(tmp_path: Path) -> None:
    """Empty trade list still writes a header row."""
    output = tmp_path / "trades.csv"

    export_trades_csv([], output)

    with output.open(encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    assert rows == [list(TRADE_CSV_COLUMNS)]
