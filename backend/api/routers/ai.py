"""
AI Natural Language Interface HTTP endpoints (Phase 10). No AuthN / AuthZ.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.deps import rate_limit_ai
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
def translate(
    body: TranslateRequest,
    _rl: None = Depends(rate_limit_ai),
) -> TranslateOkResponse | TranslateClarifyResponse:
    """
    Translate plain English into a validated Trading DSL strategy.

    Returns ``needs_clarification`` when the request is ambiguous (D-113).
    """
    return get_ai_service().translate(body, user_id=None)


@router.post(
    "/clarify",
    response_model=TranslateOkResponse | TranslateClarifyResponse,
)
def clarify(
    body: ClarifyRequest,
    _rl: None = Depends(rate_limit_ai),
) -> TranslateOkResponse | TranslateClarifyResponse:
    """Continue a clarification session with user answers."""
    return get_ai_service().clarify(body, user_id=None)


@router.post("/explain", response_model=ExplainResponse)
def explain(
    body: ExplainRequest,
    _rl: None = Depends(rate_limit_ai),
) -> ExplainResponse:
    """Explain a DSL strategy back in plain English (template)."""
    return get_ai_service().explain(body)
