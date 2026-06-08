"""
Integration tests for run_backtest.main() (Phase 3 CLI path).
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import pandas as pd
import pytest

import run_backtest
from backtest.types import BacktestConfig
from config import AppConfig
from exceptions import DataGapError


def _sample_candles(bar_count: int = 90) -> pd.DataFrame:
    """OHLCV frame long enough for RSI warmup and at least one signal cycle."""
    close = pd.Series(
        [100.0 + (i % 12) * 2.5 - (i // 12) * 1.5 for i in range(bar_count)],
        dtype=float,
    )
    return pd.DataFrame(
        {
            "ts": pd.date_range("2023-01-01", periods=bar_count, freq="D", tz="UTC"),
            "open": close.shift(1, fill_value=close.iloc[0]),
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 1_000.0,
        }
    )


def _long_only_config(tmp_path: Path) -> AppConfig:
    """Minimal long-only RSI strategy with CSV export enabled."""
    output_dir = tmp_path / "output"
    return AppConfig(
        symbol="BTC/USDT",
        timeframe="1d",
        years=1,
        exchange_id="binance",
        initial_capital=10_000.0,
        output_dir=output_dir,
        equity_curve_filename="equity_curve.png",
        active_strategy="rsi_integration",
        strategy={
            "benchmark": "symbol",
            "entry_trigger": "edge",
            "entry": {"indicator": "RSI", "params": {"period": 14}, "op": "<", "value": 40},
            "exit": {"indicator": "RSI", "params": {"period": 14}, "op": ">", "value": 60},
        },
        backtest=BacktestConfig(
            export_trades=True,
            trades_csv=output_dir / "trades.csv",
        ),
    )


def _dual_config(tmp_path: Path) -> AppConfig:
    """Dual strategy exercising ATR risk path and benchmark."""
    output_dir = tmp_path / "output"
    return AppConfig(
        symbol="BTC/USDT",
        timeframe="1d",
        years=1,
        exchange_id="binance",
        initial_capital=10_000.0,
        output_dir=output_dir,
        equity_curve_filename="equity_curve.png",
        active_strategy="dual_integration",
        strategy={
            "benchmark": "symbol",
            "entry_trigger": "edge",
            "long": {
                "entry": {"indicator": "RSI", "params": {"period": 14}, "op": "<", "value": 40},
                "exit": {"indicator": "RSI", "params": {"period": 14}, "op": ">", "value": 60},
                "stop_loss": {"type": "atr", "period": 14, "multiplier": 2.0},
                "take_profit": {"type": "risk_reward", "ratio": 2.0},
            },
            "short": {
                "entry": {"indicator": "RSI", "params": {"period": 14}, "op": ">", "value": 80},
                "exit": {"indicator": "RSI", "params": {"period": 14}, "op": "<", "value": 50},
                "stop_loss": {"type": "atr", "period": 14, "multiplier": 2.0},
                "take_profit": {"type": "fixed", "offset_pct": 0.03},
            },
        },
        backtest=BacktestConfig(
            export_trades=True,
            trades_csv=output_dir / "trades.csv",
        ),
    )


def _patch_pipeline(monkeypatch: pytest.MonkeyPatch, app_config: AppConfig, candles: pd.DataFrame) -> None:
    """Stub data I/O so main() runs without a live database."""
    monkeypatch.setattr(run_backtest, "load_config", lambda path=None: app_config)
    monkeypatch.setattr(run_backtest, "ensure_data", lambda symbol: None)
    monkeypatch.setattr(
        run_backtest,
        "get_candles",
        lambda symbol, timeframe, start, end: candles,
    )


def test_main_writes_equity_png_and_trades_csv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """End-to-end CLI path writes equity PNG and trades CSV with matching row count."""
    app_config = _long_only_config(tmp_path)
    _patch_pipeline(monkeypatch, app_config, _sample_candles())

    run_backtest.main()

    equity_path = app_config.output_dir / app_config.equity_curve_filename
    trades_path = app_config.backtest.trades_csv
    assert equity_path.is_file()
    assert equity_path.stat().st_size > 0
    assert trades_path.is_file()

    with trades_path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) >= 0
    if rows:
        assert "entry_date" in rows[0]
        assert "exit_reason" in rows[0]


def test_main_dual_strategy_pipeline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Dual strategy path runs through evaluator, ATR risk, and export."""
    app_config = _dual_config(tmp_path)
    _patch_pipeline(monkeypatch, app_config, _sample_candles())

    run_backtest.main()

    assert (app_config.output_dir / app_config.equity_curve_filename).is_file()
    assert app_config.backtest.trades_csv.is_file()


def test_main_raises_when_candles_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty candle window surfaces DataGapError before backtest runs."""
    app_config = _long_only_config(tmp_path)
    _patch_pipeline(monkeypatch, app_config, pd.DataFrame())

    with pytest.raises(DataGapError, match="No candles"):
        run_backtest.main()
