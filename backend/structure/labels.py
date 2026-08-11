"""
Swing structural labeling: HH / HL / LH / LL / EQH / EQL (D-55, D-65).
"""

from __future__ import annotations

from structure.types import SwingKind, SwingLabel, SwingPoint

DEFAULT_EQ_TOLERANCE_PCT = 0.0015


def _is_equal(price_a: float, price_b: float, tolerance_pct: float) -> bool:
    """Return True when two prices are within relative tolerance."""
    mid = (price_a + price_b) / 2.0
    if mid <= 0.0:
        return price_a == price_b
    return abs(price_a - price_b) / mid <= tolerance_pct


def _label_vs_prior(
    kind: SwingKind,
    price: float,
    prior_price: float,
    tolerance_pct: float,
) -> SwingLabel:
    """Label a swing relative to the prior swing of the same kind."""
    if _is_equal(price, prior_price, tolerance_pct):
        return SwingLabel.EQH if kind is SwingKind.HIGH else SwingLabel.EQL
    if price > prior_price:
        return SwingLabel.HH if kind is SwingKind.HIGH else SwingLabel.HL
    return SwingLabel.LH if kind is SwingKind.HIGH else SwingLabel.LL


def label_swings(
    swings: list[SwingPoint],
    *,
    tolerance_pct: float = DEFAULT_EQ_TOLERANCE_PCT,
) -> list[SwingPoint]:
    """
    Assign structural labels by comparing each swing to the prior same-kind swing.

    Args:
        swings: Detected swings in time order (mixed highs and lows allowed).
        tolerance_pct: Relative equality band for EQH/EQL. Default 0.15%.

    Returns:
        New list of swings with labels set. Input objects are not mutated.

    Raises:
        ValueError: If tolerance_pct is negative.
    """
    if tolerance_pct < 0.0:
        raise ValueError("tolerance_pct must be >= 0")

    last_high: SwingPoint | None = None
    last_low: SwingPoint | None = None
    labeled: list[SwingPoint] = []

    for swing in swings:
        if swing.kind is SwingKind.HIGH:
            if last_high is None:
                label = SwingLabel.FIRST
            else:
                label = _label_vs_prior(SwingKind.HIGH, swing.price, last_high.price, tolerance_pct)
            updated = SwingPoint(
                index=swing.index,
                ts=swing.ts,
                price=swing.price,
                kind=swing.kind,
                label=label,
                confirmed=swing.confirmed,
                confirmation_index=swing.confirmation_index,
            )
            last_high = updated
            labeled.append(updated)
        else:
            if last_low is None:
                label = SwingLabel.FIRST
            else:
                label = _label_vs_prior(SwingKind.LOW, swing.price, last_low.price, tolerance_pct)
            updated = SwingPoint(
                index=swing.index,
                ts=swing.ts,
                price=swing.price,
                kind=swing.kind,
                label=label,
                confirmed=swing.confirmed,
                confirmation_index=swing.confirmation_index,
            )
            last_low = updated
            labeled.append(updated)

    return labeled
