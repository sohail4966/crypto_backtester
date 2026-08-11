"""
Market structure detection: swings, labels, S/R, trend, and multi-TF context.
"""

from structure.context import StructureContext
from structure.labels import DEFAULT_EQ_TOLERANCE_PCT, label_swings
from structure.levels import DEFAULT_LEVEL_COUNT, structure_levels
from structure.pipeline import analyze_structure
from structure.swings import DEFAULT_LEFT_BARS, DEFAULT_RIGHT_BARS, detect_swings
from structure.trend import classify_trend
from structure.types import (
    StructureLevels,
    StructureResult,
    SwingKind,
    SwingLabel,
    SwingPoint,
    Trend,
)

__all__ = [
    "DEFAULT_EQ_TOLERANCE_PCT",
    "DEFAULT_LEFT_BARS",
    "DEFAULT_LEVEL_COUNT",
    "DEFAULT_RIGHT_BARS",
    "StructureContext",
    "StructureLevels",
    "StructureResult",
    "SwingKind",
    "SwingLabel",
    "SwingPoint",
    "Trend",
    "analyze_structure",
    "classify_trend",
    "detect_swings",
    "label_swings",
    "structure_levels",
]
