"""
Tests for config loading.
"""

from pathlib import Path

import yaml

from config import is_dual_strategy, load_config


def test_load_config_reads_strategy_and_symbol() -> None:
    """Default config.yaml provides symbol and the active named strategy."""
    app_config = load_config()
    assert "/" in app_config.symbol
    assert app_config.active_strategy == "full_stack_confluence"
    assert is_dual_strategy(app_config.strategy)
    assert app_config.strategy["long"]["entry"]["all"][0]["indicator"] == "ADX"
    assert app_config.strategy.get("entry_trigger", "edge") in {"edge", "level"}
    assert app_config.initial_capital == 10_000.0


def test_load_config_includes_dual_strategy_definition() -> None:
    """Named strategies include multi-indicator long/short legs with risk blocks."""
    raw = yaml.safe_load((Path(__file__).resolve().parents[2] / "config.yaml").read_text(encoding="utf-8"))
    strategy = raw["strategies"]["full_stack_confluence"]
    assert strategy.get("entry_trigger") == "edge"
    assert "long" in strategy
    assert "short" in strategy
    assert strategy["long"]["entry"]["all"][0]["indicator"] == "ADX"
    assert strategy["long"]["stop_loss"]["type"] == "atr_trail"
    assert strategy["long"]["take_profit"]["type"] == "risk_reward"
    assert strategy["short"]["stop_loss"]["type"] == "atr"
    assert strategy["short"]["take_profit"]["type"] == "fixed"
