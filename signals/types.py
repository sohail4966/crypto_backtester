"""
Typed structures for the minimal POC signal dict schema.
"""

from __future__ import annotations

from typing import NotRequired, TypedDict


class SignalCondition(TypedDict):
    """A single indicator-based condition (entry or exit leg)."""

    indicator: str
    op: str
    value: float
    params: NotRequired[dict[str, int | float]]


class Strategy(TypedDict):
    """Long-only strategy with separate entry and exit conditions."""

    entry: SignalCondition
    exit: SignalCondition
