"""
Tests for signals.evaluator.
"""

import pandas as pd
import pytest

from exceptions import InvalidSignalError
from signals.evaluator import evaluate_signals
from signals.types import Strategy


def _sample_candles() -> pd.DataFrame:
    """Minimal OHLCV frame for signal tests."""
    return pd.DataFrame(
        {
            "ts": pd.date_range("2024-01-01", periods=30, freq="D", tz="UTC"),
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": [100 + (i % 5) for i in range(30)],
            "volume": 1000.0,
        }
    )


def test_evaluate_signals_unknown_indicator_raises_invalid_signal_error() -> None:
    """Unknown indicator names raise InvalidSignalError."""
    strategy: Strategy = {
        "entry": {"indicator": "MACD", "op": "<", "value": 0},
        "exit": {"indicator": "RSI", "params": {"period": 14}, "op": ">", "value": 70},
    }
    with pytest.raises(InvalidSignalError, match="Unknown indicator"):
        evaluate_signals(_sample_candles(), strategy)


def test_evaluate_signals_unknown_operator_raises_invalid_signal_error() -> None:
    """Unknown operators raise InvalidSignalError."""
    strategy: Strategy = {
        "entry": {"indicator": "RSI", "params": {"period": 14}, "op": "!=", "value": 30},
        "exit": {"indicator": "RSI", "params": {"period": 14}, "op": ">", "value": 70},
    }
    with pytest.raises(InvalidSignalError, match="Unknown operator"):
        evaluate_signals(_sample_candles(), strategy)


def test_evaluate_signals_rsi_entry_returns_boolean_series() -> None:
    """RSI entry condition produces a boolean Series aligned to candles."""
    strategy: Strategy = {
        "entry": {"indicator": "RSI", "params": {"period": 14}, "op": "<", "value": 30},
        "exit": {"indicator": "RSI", "params": {"period": 14}, "op": ">", "value": 70},
    }
    candles = _sample_candles()
    entry_signals, exit_signals = evaluate_signals(candles, strategy)
    assert entry_signals.dtype == bool
    assert len(entry_signals) == len(candles)
    assert len(exit_signals) == len(candles)


def test_evaluate_signals_macd_hist_entry_returns_boolean_series() -> None:
    """MACD_HIST condition resolves via close-only registry key (D-32)."""
    strategy: Strategy = {
        "entry": {
            "indicator": "MACD_HIST",
            "params": {"fast": 12, "slow": 26, "signal": 9},
            "op": ">",
            "value": 0,
        },
        "exit": {"indicator": "RSI", "params": {"period": 14}, "op": ">", "value": 70},
    }
    candles = _sample_candles()
    entry_signals, exit_signals = evaluate_signals(candles, strategy)
    assert entry_signals.dtype == bool
    assert len(entry_signals) == len(candles)
    assert len(exit_signals) == len(candles)


def test_evaluate_signals_mfi_routes_full_ohlcv() -> None:
    """MFI receives high, low, close, and volume via INDICATOR_META routing (D-31)."""
    strategy: Strategy = {
        "entry": {"indicator": "MFI", "params": {"period": 14}, "op": "<", "value": 20},
        "exit": {"indicator": "RSI", "params": {"period": 14}, "op": ">", "value": 80},
    }
    candles = _sample_candles()
    entry_signals, exit_signals = evaluate_signals(candles, strategy)
    assert entry_signals.dtype == bool
    assert len(entry_signals) == len(candles)
    assert len(exit_signals) == len(candles)


def test_evaluate_signals_invalid_indicator_params_raise_invalid_signal_error() -> None:
    """Indicator ValueError from bad params maps to InvalidSignalError (D-30)."""
    strategy: Strategy = {
        "entry": {"indicator": "RSI", "params": {"period": 0}, "op": "<", "value": 30},
        "exit": {"indicator": "RSI", "params": {"period": 14}, "op": ">", "value": 70},
    }
    with pytest.raises(InvalidSignalError, match="period must be >= 2"):
        evaluate_signals(_sample_candles(), strategy)

