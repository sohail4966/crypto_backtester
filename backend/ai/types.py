"""
Shared types for the Phase 10 AI translation layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


ClarificationStatus = Literal["ok", "needs_clarification"]


@dataclass(frozen=True)
class ClarificationQuestion:
    """A single clarifying question for ambiguous NL input."""

    id: str
    prompt: str
    options: list[str] = field(default_factory=list)


@dataclass
class TranslateOk:
    """Successful NL → DSL translation."""

    status: Literal["ok"] = "ok"
    strategy: dict[str, Any] = field(default_factory=dict)
    explanation: str = ""


@dataclass
class TranslateNeedsClarification:
    """Ambiguous NL input requiring user answers before a strategy is emitted."""

    status: Literal["needs_clarification"] = "needs_clarification"
    session_id: str = ""
    questions: list[ClarificationQuestion] = field(default_factory=list)


TranslateOutcome = TranslateOk | TranslateNeedsClarification
