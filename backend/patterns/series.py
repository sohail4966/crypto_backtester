"""
Convert pattern hits into evaluator-compatible boolean Series.
"""

from __future__ import annotations

import pandas as pd

from patterns.types import PatternHit, PatternName


def empty_signal(index: pd.DatetimeIndex) -> pd.Series:
    """Return an all-False boolean Series aligned to ``index``."""
    return pd.Series(False, index=index, dtype=bool)


def hits_to_signals(
    hits: list[PatternHit],
    index: pd.DatetimeIndex,
    *,
    names: list[PatternName] | None = None,
) -> dict[str, pd.Series]:
    """
    Pack hits into sparse boolean Series keyed by pattern name.

    True only at each hit's ``end_index`` (confirmation bar). Multiple hits for the
    same name OR together on the Series.
    """
    keys = [n.value for n in names] if names is not None else sorted({h.name.value for h in hits})
    out: dict[str, pd.Series] = {k: empty_signal(index) for k in keys}
    n = len(index)
    for hit in hits:
        key = hit.name.value
        if key not in out:
            out[key] = empty_signal(index)
        if 0 <= hit.end_index < n:
            out[key].iloc[hit.end_index] = True
    return out
