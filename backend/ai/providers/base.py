"""
LLM provider protocol.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """Pluggable LLM backend for NL → DSL translation."""

    name: str

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """
        Return model completion text (expected to be JSON).

        Args:
            system_prompt: System instructions including DSL schema.
            user_prompt: User NL (+ optional clarifications).

        Returns:
            Raw completion string.
        """
        ...
