"""
Tests for config loading.
"""

from config import load_config


def test_load_config_reads_strategy_and_symbol() -> None:
    """Default config.yaml provides symbol and RSI strategy legs."""
    app_config = load_config()
    assert app_config.symbol == "BTC/USDT"
    assert app_config.strategy["entry"]["indicator"] == "RSI"
    assert app_config.initial_capital == 10_000.0
