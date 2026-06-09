"""
Tests for Phase 3 backtest config parsing.
"""

from pathlib import Path

import pytest
import yaml

from config import load_config


def test_load_config_parses_backtest_block() -> None:
    """Production config includes slippage, commission, and export settings."""
    app_config = load_config()
    assert app_config.backtest.slippage_bps == 5.0
    assert app_config.backtest.commission.type == "percent"
    assert app_config.backtest.commission.rate == 0.001
    assert app_config.backtest.sizing.mode == "full_capital"
    assert app_config.backtest.export_trades is True
    assert app_config.backtest.trades_csv == Path("output/trades.csv")


def test_load_config_defaults_zero_fees_without_backtest_block(tmp_path: Path) -> None:
    """Missing backtest block uses zero slippage and commission for test stability."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.dump(
            {
                "symbol": "BTC/USDT",
                "timeframe": "1d",
                "years": 1,
                "exchange_id": "binance",
                "initial_capital": 10000.0,
                "active_strategy": "simple",
                "strategies": {
                    "simple": {
                        "entry": {"indicator": "RSI", "params": {"period": 14}, "op": "<", "value": 30},
                        "exit": {"indicator": "RSI", "params": {"period": 14}, "op": ">", "value": 70},
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    app_config = load_config(config_path)
    assert app_config.backtest.slippage_bps == 0.0
    assert app_config.backtest.commission.rate == 0.0


def test_load_config_rejects_risk_pct_without_stop_loss(tmp_path: Path) -> None:
    """risk_pct sizing requires stop_loss per D-51."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.dump(
            {
                "symbol": "BTC/USDT",
                "timeframe": "1d",
                "years": 1,
                "exchange_id": "binance",
                "initial_capital": 10000.0,
                "active_strategy": "bad",
                "strategies": {
                    "bad": {
                        "long": {
                            "entry": {"indicator": "RSI", "op": "<", "value": 30},
                            "exit": {"indicator": "RSI", "op": ">", "value": 70},
                            "sizing": {"mode": "risk_pct", "risk_pct": 0.01},
                        },
                        "short": {
                            "entry": {"indicator": "RSI", "op": ">", "value": 70},
                            "exit": {"indicator": "RSI", "op": "<", "value": 30},
                            "stop_loss": {"type": "atr", "period": 14, "multiplier": 2.0},
                            "take_profit": {"type": "risk_reward", "ratio": 2.0},
                        },
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="risk_pct sizing requires stop_loss"):
        load_config(config_path)
