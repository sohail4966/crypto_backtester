"""
Support and resistance levels from confirmed swings (D-57, D-64).
"""

from __future__ import annotations

from structure.types import StructureLevels, SwingKind, SwingPoint

DEFAULT_LEVEL_COUNT = 3


def structure_levels(
    swings: list[SwingPoint],
    *,
    k: int = DEFAULT_LEVEL_COUNT,
) -> StructureLevels:
    """
    Build discrete S/R from the last ``k`` confirmed swing lows / highs.

    Args:
        swings: Labeled swings (provisional ignored).
        k: Maximum levels per side. Default 3.

    Returns:
        ``StructureLevels`` with support and resistance most-recent-first.

    Raises:
        ValueError: If k is less than 1.
    """
    if k < 1:
        raise ValueError("k must be >= 1")

    confirmed = [s for s in swings if s.confirmed]
    highs = [s.price for s in confirmed if s.kind is SwingKind.HIGH]
    lows = [s.price for s in confirmed if s.kind is SwingKind.LOW]
    # Chronological lists → reverse for most-recent-first, then cap at k.
    resistance = list(reversed(highs[-k:])) if highs else []
    support = list(reversed(lows[-k:])) if lows else []
    return StructureLevels(support=support, resistance=resistance)
