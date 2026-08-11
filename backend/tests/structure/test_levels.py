"""
Tests for structure S/R levels.
"""

from __future__ import annotations

import pandas as pd

from structure.levels import structure_levels
from structure.types import SwingKind, SwingLabel, SwingPoint


def _swing(index: int, price: float, kind: SwingKind, *, confirmed: bool) -> SwingPoint:
    """Build a swing for level tests."""
    return SwingPoint(
        index=index,
        ts=pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=index),
        price=price,
        kind=kind,
        label=SwingLabel.FIRST,
        confirmed=confirmed,
        confirmation_index=index + 2 if confirmed else None,
    )


def test_levels_recency_first_and_k_cap() -> None:
    """Support/resistance are most-recent-first and capped at k."""
    swings = [
        _swing(0, 90.0, SwingKind.LOW, confirmed=True),
        _swing(1, 100.0, SwingKind.HIGH, confirmed=True),
        _swing(2, 91.0, SwingKind.LOW, confirmed=True),
        _swing(3, 101.0, SwingKind.HIGH, confirmed=True),
        _swing(4, 92.0, SwingKind.LOW, confirmed=True),
        _swing(5, 102.0, SwingKind.HIGH, confirmed=True),
        _swing(6, 93.0, SwingKind.LOW, confirmed=True),
        _swing(7, 103.0, SwingKind.HIGH, confirmed=True),
    ]
    levels = structure_levels(swings, k=3)
    assert levels.support == [93.0, 92.0, 91.0]
    assert levels.resistance == [103.0, 102.0, 101.0]


def test_levels_ignore_provisional() -> None:
    """Provisional swings never enter S/R lists."""
    swings = [
        _swing(0, 90.0, SwingKind.LOW, confirmed=True),
        _swing(1, 100.0, SwingKind.HIGH, confirmed=True),
        _swing(2, 95.0, SwingKind.LOW, confirmed=False),
        _swing(3, 110.0, SwingKind.HIGH, confirmed=False),
    ]
    levels = structure_levels(swings, k=3)
    assert levels.support == [90.0]
    assert levels.resistance == [100.0]
