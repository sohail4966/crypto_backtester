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
