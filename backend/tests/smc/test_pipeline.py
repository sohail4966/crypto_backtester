"""Pipeline + named condition / evaluator integration tests."""

from __future__ import annotations

from smc.config import SmcConfig
from smc.pipeline import analyze_smc
from smc.types import SmcConcept
from signals.evaluator import evaluate_signals
from tests.smc.helpers import ohlcv


def _sample():
    return ohlcv(
        [
            (10, 10.2, 9.8, 10.0),
            (10, 10.1, 9.7, 9.9),
            (9.9, 10.0, 8.0, 8.2),
            (8.2, 8.5, 8.1, 8.4),
            (8.4, 8.6, 8.2, 8.5),
            (8.5, 12.0, 8.4, 11.5),
            (11.5, 11.6, 11.0, 11.2),
            (11.2, 11.4, 10.8, 11.0),
            (11.0, 11.1, 9.0, 9.2),
            (9.2, 9.5, 9.1, 9.4),
            (9.4, 9.6, 9.2, 9.5),
            (9.5, 13.0, 9.4, 12.5),
            (12.5, 12.6, 12.0, 12.2),
            (12.2, 12.4, 11.8, 12.0),
            (12.0, 12.2, 11.5, 11.6),
            (11.6, 14.0, 11.5, 13.8),
            # bullish FVG windows later
            (13.8, 13.9, 13.7, 13.85),
            (13.85, 14.0, 13.8, 13.9),
            (13.9, 16.0, 15.0, 15.5),  # FVG if high[i-2] < low[i]
        ]
    )


def test_analyze_smc_returns_multiple_concepts():
    df = _sample()
    result = analyze_smc(df, SmcConfig(left_bars=2, right_bars=2))
    concepts = {e.concept for e in result.events}
    assert SmcConcept.BOS in concepts or SmcConcept.CHOCH in concepts
    assert SmcConcept.ORDER_BLOCK in concepts or SmcConcept.FVG in concepts


def test_evaluator_smc_named_condition():
    df = _sample()
    strategy = {
        "entry": {"smc": "bos", "side": "bullish", "params": {"left_bars": 2, "right_bars": 2}},
        "exit": {"smc": "choch", "side": "bearish", "params": {"left_bars": 2, "right_bars": 2}},
        "entry_trigger": "level",
    }
    entry, exit_ = evaluate_signals(df, strategy)
    assert entry.dtype == bool or str(entry.dtype) == "bool"
    assert len(entry) == len(df)
    # At least one bullish BOS on this fixture
    assert bool(entry.any())


def test_unknown_smc_concept_raises():
    from exceptions import InvalidSignalError
    import pytest

    df = _sample()
    with pytest.raises(InvalidSignalError):
        evaluate_signals(
            df,
            {
                "entry": {"smc": "not_a_thing"},
                "exit": {"smc": "bos"},
            },
        )
