"""
AI natural language → Trading DSL translation layer (Phase 10).
"""

from ai.explain import explain_strategy
from ai.translate import apply_clarification, translate_nl

__all__ = [
    "apply_clarification",
    "explain_strategy",
    "translate_nl",
]
