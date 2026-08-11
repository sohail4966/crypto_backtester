"""
Pydantic schemas for Phase 10 AI endpoints.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class TranslateRequest(BaseModel):
    """Natural language strategy description."""

    text: str = Field(..., min_length=1, description="Plain-English strategy")


class ClarifyRequest(BaseModel):
    """Answers to a prior clarification session."""

    session_id: str = Field(..., min_length=1)
    answers: dict[str, str] = Field(..., min_length=1)


class ExplainRequest(BaseModel):
    """DSL strategy to explain in English."""

    strategy: dict[str, Any]


class ClarificationQuestionResponse(BaseModel):
    """One clarifying question returned to the client."""

    id: str
    prompt: str
    options: list[str] = Field(default_factory=list)


class TranslateOkResponse(BaseModel):
    """Successful translation response."""

    status: Literal["ok"] = "ok"
    strategy: dict[str, Any]
    explanation: str = ""


class TranslateClarifyResponse(BaseModel):
    """Ambiguous translation requiring user input."""

    status: Literal["needs_clarification"] = "needs_clarification"
    session_id: str
    questions: list[ClarificationQuestionResponse]


class ExplainResponse(BaseModel):
    """Plain-English explanation of a strategy."""

    explanation: str
