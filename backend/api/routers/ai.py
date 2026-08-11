"""
AI Natural Language Interface HTTP endpoints (Phase 10).
"""

from __future__ import annotations

from fastapi import APIRouter

from api.schemas.ai import (
    ClarifyRequest,
    ExplainRequest,
    ExplainResponse,
    TranslateClarifyResponse,
    TranslateOkResponse,
    TranslateRequest,
)
from api.services.ai_service import get_ai_service

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post(
    "/translate",
    response_model=TranslateOkResponse | TranslateClarifyResponse,
)
def translate(body: TranslateRequest) -> TranslateOkResponse | TranslateClarifyResponse:
    """
    Translate plain English into a validated Trading DSL strategy.

    Returns ``needs_clarification`` when the request is ambiguous (D-113).
    """
    return get_ai_service().translate(body)


@router.post(
    "/clarify",
    response_model=TranslateOkResponse | TranslateClarifyResponse,
)
def clarify(body: ClarifyRequest) -> TranslateOkResponse | TranslateClarifyResponse:
    """Continue a clarification session with user answers."""
    return get_ai_service().clarify(body)


@router.post("/explain", response_model=ExplainResponse)
def explain(body: ExplainRequest) -> ExplainResponse:
    """Explain a DSL strategy back in plain English (template)."""
    return get_ai_service().explain(body)
