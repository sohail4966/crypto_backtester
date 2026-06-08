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


def test_evaluate_signals_all_group_requires_every_leg() -> None:
    """AND groups only fire when every nested leg is true."""
    strategy: Strategy = {
        "entry": {
            "all": [
                {"indicator": "RSI", "params": {"period": 14}, "op": "<", "value": 100},
                {"indicator": "ADX", "params": {"period": 14}, "op": ">", "value": -100},
            ]
        },
        "exit": {"indicator": "RSI", "params": {"period": 14}, "op": ">", "value": 70},
    }
    candles = _sample_candles()
    entry_signals, exit_signals = evaluate_signals(candles, strategy)
    assert entry_signals.dtype == bool
    assert entry_signals.any()
    assert len(exit_signals) == len(candles)


def test_evaluate_dual_strategy_returns_four_signal_series() -> None:
    """Dual strategies evaluate separate long and short legs."""
    from signals.evaluator import evaluate_dual_strategy

    strategy = {
        "long": {
            "entry": {"indicator": "RSI", "params": {"period": 14}, "op": "<", "value": 30},
            "exit": {"indicator": "RSI", "params": {"period": 14}, "op": ">", "value": 70},
            "stop_loss": {"type": "atr", "period": 14, "multiplier": 2.0},
            "take_profit": {"type": "risk_reward", "ratio": 2.0},
        },
        "short": {
            "entry": {"indicator": "RSI", "params": {"period": 14}, "op": ">", "value": 70},
            "exit": {"indicator": "RSI", "params": {"period": 14}, "op": "<", "value": 30},
            "stop_loss": {"type": "atr", "period": 14, "multiplier": 2.0},
            "take_profit": {"type": "risk_reward", "ratio": 2.0},
        },
    }
    candles = _sample_candles()
    signals = evaluate_dual_strategy(candles, strategy)
    assert set(signals) == {"long_entry", "long_exit", "short_entry", "short_exit"}
    for series in signals.values():
        assert series.dtype == bool
        assert len(series) == len(candles)


def test_evaluate_signals_ema_cross_compare_returns_boolean_series() -> None:
    """EMA legs can compare against another indicator via compare."""
    strategy: Strategy = {
        "entry": {
            "indicator": "EMA",
            "params": {"period": 5},
            "op": ">",
            "compare": {"indicator": "EMA", "params": {"period": 10}},
        },
        "exit": {
            "indicator": "EMA",
            "params": {"period": 5},
            "op": "<",
            "compare": {"indicator": "EMA", "params": {"period": 10}},
        },
    }
    candles = _sample_candles()
    entry_signals, exit_signals = evaluate_signals(candles, strategy)
    assert entry_signals.dtype == bool
    assert len(entry_signals) == len(candles)
    assert len(exit_signals) == len(candles)


def test_evaluate_signals_supertrend_above_close_compare() -> None:
    """SuperTrend can be compared against close for trend direction."""
    strategy: Strategy = {
        "entry": {
            "indicator": "SUPERTREND",
            "params": {"period": 5, "multiplier": 2.0},
            "op": "<",
            "compare": "close",
        },
        "exit": {
            "indicator": "SUPERTREND",
            "params": {"period": 5, "multiplier": 2.0},
            "op": ">",
            "compare": "close",
        },
    }
    candles = _sample_candles()
    entry_signals, exit_signals = evaluate_signals(candles, strategy)
    assert entry_signals.dtype == bool
    assert len(entry_signals) == len(candles)


def test_evaluate_signals_invalid_indicator_params_raise_invalid_signal_error() -> None:
    """Indicator ValueError from bad params maps to InvalidSignalError (D-30)."""
    strategy: Strategy = {
        "entry": {"indicator": "RSI", "params": {"period": 0}, "op": "<", "value": 30},
        "exit": {"indicator": "RSI", "params": {"period": 14}, "op": ">", "value": 70},
    }
    with pytest.raises(InvalidSignalError, match="period must be >= 2"):
        evaluate_signals(_sample_candles(), strategy)

