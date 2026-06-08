"""
Tests for buy-and-hold benchmark (Phase 3 Step 5).
"""

import pandas as pd
import pytest

from backtest.benchmark import compute_buy_and_hold_return


def test_buy_and_hold_return_matches_manual_calculation() -> None:
    """Benchmark return equals (last_close / first_close) - 1."""
    candles = pd.DataFrame(
        {
            "ts": pd.date_range("2024-01-01", periods=3, freq="D", tz="UTC"),
            "close": [100.0, 110.0, 125.0],
        }
    )
    result = compute_buy_and_hold_return(candles)
    assert result == pytest.approx(0.25)
