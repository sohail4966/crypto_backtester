"""
Smart Money Concepts (SMC) detectors — ICT-leaning, configurable defaults.

This package documents one interpretation of SMC terminology. Definitions vary
across educators; see ``SmcConfig`` and ``PHASE_7_HLD.md`` for knobs and notes.
"""

from smc.config import SmcConfig
from smc.conditions import evaluate_smc_leg
from smc.pipeline import analyze_smc
from smc.types import (
    FvgInvalidation,
    SmcConcept,
    SmcEvent,
    SmcResult,
    SmcSide,
)

__all__ = [
    "FvgInvalidation",
    "SmcConcept",
    "SmcConfig",
    "SmcEvent",
    "SmcResult",
    "SmcSide",
    "analyze_smc",
    "evaluate_smc_leg",
]
