"""
Tests for config loading.
"""

from config import is_dual_strategy, load_config


def test_load_config_reads_strategy_and_symbol() -> None:
    """Default config.yaml provides symbol and RSI strategy legs."""
    app_config = load_config()
    assert "/" in app_config.symbol
    assert app_config.active_strategy in {
        "rsi_mean_reversion",
        "trend_momentum",
        "golden_trend",
        "supertrend_ema_dual",
    }
    if app_config.active_strategy == "rsi_mean_reversion":
        assert app_config.strategy["entry"]["indicator"] == "RSI"
        assert not is_dual_strategy(app_config.strategy)
    elif app_config.active_strategy in {"trend_momentum", "supertrend_ema_dual"}:
        assert is_dual_strategy(app_config.strategy)
    elif app_config.active_strategy == "golden_trend":
        assert app_config.strategy["entry"]["all"][0]["indicator"] == "EMA"
    assert app_config.initial_capital == 10_000.0


def test_load_config_includes_dual_strategy_definition() -> None:
    """Named strategies include the multi-indicator long/short trend_momentum block."""
    app_config = load_config()
    trend = app_config.strategy if app_config.active_strategy == "trend_momentum" else None
    # Read trend_momentum directly from the YAML-backed strategies map via load_config swap
    from pathlib import Path

    import yaml

    raw = yaml.safe_load((Path(__file__).resolve().parents[2] / "config.yaml").read_text(encoding="utf-8"))
    trend = raw["strategies"]["trend_momentum"]
    assert "long" in trend
    assert "short" in trend
    assert trend["long"]["entry"]["all"][0]["indicator"] == "ADX"
    assert trend["long"]["stop_loss"]["type"] == "atr"
    assert trend["long"]["take_profit"]["type"] == "risk_reward"

    golden = raw["strategies"]["golden_trend"]
    assert golden["entry"]["all"][0]["indicator"] == "EMA"
    assert golden["entry"]["all"][3]["indicator"] == "SUPERTREND"

    dual = raw["strategies"]["supertrend_ema_dual"]
    assert dual["long"]["entry"]["all"][0]["indicator"] == "SUPERTREND"
    assert dual["short"]["entry"]["all"][3]["indicator"] == "SMA"
