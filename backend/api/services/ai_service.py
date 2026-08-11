"""
API service wrapper for Phase 10 AI translation.
"""

from __future__ import annotations

from typing import Any

from ai.explain import explain_strategy
from ai.providers import LLMProvider, get_provider
from ai.sessions import get_session_store, reset_session_store
from ai.translate import AITranslateError, apply_clarification, translate_nl
from ai.types import TranslateNeedsClarification, TranslateOk, TranslateOutcome
from api.exceptions import ApiError, NotFoundError, ValidationError
from api.schemas.ai import (
    ClarifyRequest,
    ClarificationQuestionResponse,
    ExplainRequest,
    ExplainResponse,
    TranslateClarifyResponse,
    TranslateOkResponse,
    TranslateRequest,
)
from dsl.validate import validate_strategy
from exceptions import InvalidSignalError


def _map_error(exc: AITranslateError) -> ApiError:
    """Map AITranslateError codes to HTTP ApiError."""
    if exc.code == "SESSION_NOT_FOUND":
        return NotFoundError(exc.code, exc.message)
    if exc.code == "PROVIDER_ERROR":
        return ApiError(exc.code, exc.message, status_code=502)
    return ValidationError(exc.code, exc.message)


def _to_response(
    outcome: TranslateOutcome,
) -> TranslateOkResponse | TranslateClarifyResponse:
    """Convert domain outcome to response models."""
    if isinstance(outcome, TranslateOk):
        return TranslateOkResponse(
            strategy=outcome.strategy,
            explanation=outcome.explanation,
        )
    assert isinstance(outcome, TranslateNeedsClarification)
    return TranslateClarifyResponse(
        session_id=outcome.session_id,
        questions=[
            ClarificationQuestionResponse(
                id=q.id,
                prompt=q.prompt,
                options=list(q.options),
            )
            for q in outcome.questions
        ],
    )


class AIService:
    """Orchestrates NL → DSL translation for HTTP handlers."""

    def __init__(self, provider: LLMProvider | None = None) -> None:
        self._provider = provider

    @property
    def provider(self) -> LLMProvider:
        """Resolve provider (lazy so env changes in tests apply)."""
        return self._provider if self._provider is not None else get_provider()

    def translate(
        self,
        body: TranslateRequest,
    ) -> TranslateOkResponse | TranslateClarifyResponse:
        """Translate NL text into DSL or clarification questions."""
        try:
            outcome = translate_nl(
                body.text,
                provider=self.provider,
                store=get_session_store(),
            )
        except AITranslateError as exc:
            raise _map_error(exc) from exc
        return _to_response(outcome)

    def clarify(
        self,
        body: ClarifyRequest,
    ) -> TranslateOkResponse | TranslateClarifyResponse:
        """Apply clarification answers and continue translation."""
        try:
            outcome = apply_clarification(
                body.session_id,
                body.answers,
                provider=self.provider,
                store=get_session_store(),
            )
        except AITranslateError as exc:
            raise _map_error(exc) from exc
        return _to_response(outcome)

    def explain(self, body: ExplainRequest) -> ExplainResponse:
        """Validate strategy then return template English explanation."""
        try:
            model = validate_strategy(body.strategy)
        except InvalidSignalError as exc:
            raise ValidationError("INVALID_DSL", str(exc)) from exc
        strategy_dict: dict[str, Any] = model.model_dump(exclude_none=True)
        return ExplainResponse(explanation=explain_strategy(strategy_dict))


_service: AIService | None = None


def get_ai_service() -> AIService:
    """Return process-wide AIService singleton."""
    global _service
    if _service is None:
        _service = AIService()
    return _service


def reset_ai_service() -> None:
    """Reset service + sessions (tests)."""
    global _service
    _service = None
    reset_session_store()
