"""
Tests for swing structural labels.
"""

from __future__ import annotations

import pandas as pd

from structure.labels import label_swings
from structure.types import SwingKind, SwingLabel, SwingPoint


def _swing(
    index: int,
    price: float,
    kind: SwingKind,
    *,
    confirmed: bool = True,
) -> SwingPoint:
    """Build a unlabeled swing for label tests."""
    return SwingPoint(
        index=index,
        ts=pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=index),
        price=price,
        kind=kind,
        label=SwingLabel.FIRST,
        confirmed=confirmed,
        confirmation_index=index + 2 if confirmed else None,
    )


def test_labels_hh_hl_lh_ll() -> None:
    """Directional comparisons assign HH/HL/LH/LL."""
    swings = [
        _swing(0, 100.0, SwingKind.HIGH),
        _swing(1, 90.0, SwingKind.LOW),
        _swing(2, 110.0, SwingKind.HIGH),
        _swing(3, 95.0, SwingKind.LOW),
        _swing(4, 105.0, SwingKind.HIGH),
        _swing(5, 85.0, SwingKind.LOW),
    ]
    labeled = label_swings(swings, tolerance_pct=0.0015)
    by_index = {s.index: s for s in labeled}
    assert by_index[0].label is SwingLabel.FIRST
    assert by_index[1].label is SwingLabel.FIRST
    assert by_index[2].label is SwingLabel.HH
    assert by_index[3].label is SwingLabel.HL
    assert by_index[4].label is SwingLabel.LH
    assert by_index[5].label is SwingLabel.LL


def test_equal_high_within_tolerance() -> None:
    """Nearly equal highs become EQH within default-like tolerance."""
    swings = [
        _swing(0, 100.0, SwingKind.HIGH),
        _swing(1, 100.1, SwingKind.HIGH),  # 0.1% vs mid ~100.05
    ]
    labeled = label_swings(swings, tolerance_pct=0.0015)
    assert labeled[0].label is SwingLabel.FIRST
    assert labeled[1].label is SwingLabel.EQH


def test_equal_low_outside_tolerance_is_directional() -> None:
    """Outside tolerance stays directional (HL)."""
    swings = [
        _swing(0, 100.0, SwingKind.LOW),
        _swing(1, 101.0, SwingKind.LOW),  # ~1% — well outside 0.15%
    ]
    labeled = label_swings(swings, tolerance_pct=0.0015)
    assert labeled[1].label is SwingLabel.HL
