"""
Configurable SMC detector defaults (ICT-leaning interpretation).
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace

from smc.types import FvgInvalidation


@dataclass(frozen=True)
class SmcConfig:
    """
    Parameters for SMC detectors.

    Defaults follow an ICT-leaning reading (D-96). Every field is overridable via
    named-condition ``params``.
    """

    left_bars: int = 5
    right_bars: int = 5
    fvg_invalidation: FvgInvalidation = FvgInvalidation.FULL_FILL
    fvg_min_gap_pct: float = 0.0
    ob_use_wick_range: bool = False

    @classmethod
    def from_params(cls, params: dict | None) -> SmcConfig:
        """Build config from a plain dict (signal condition params)."""
        if not params:
            return cls()
        allowed = {f.name for f in fields(cls)}
        kwargs: dict = {}
        for key, value in params.items():
            if key not in allowed:
                raise ValueError(f"Unknown SmcConfig param: {key}")
            if key == "fvg_invalidation":
                kwargs[key] = FvgInvalidation(value)
            else:
                kwargs[key] = value
        return replace(cls(), **kwargs)
