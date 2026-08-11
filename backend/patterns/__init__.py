"""
Pattern recognition: candlesticks, classical chart patterns, and divergences.
"""

from patterns.candles import detect_candlestick_patterns
from patterns.classical import detect_classical_patterns
from patterns.divergence import detect_divergences
from patterns.pipeline import analyze_patterns
from patterns.series import hits_to_signals
from patterns.types import PatternFamily, PatternHit, PatternName, PatternResult

__all__ = [
    "PatternFamily",
    "PatternHit",
    "PatternName",
    "PatternResult",
    "analyze_patterns",
    "detect_candlestick_patterns",
    "detect_classical_patterns",
    "detect_divergences",
    "hits_to_signals",
]
