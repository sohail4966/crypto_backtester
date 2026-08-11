"""
NL → DSL translation with validation gate (D-113, D-114).
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

from ai.explain import explain_strategy
from ai.prompt import build_system_prompt, build_user_prompt
from ai.providers import LLMProvider, get_provider
from ai.providers.openai_compat import ProviderHTTPError
from ai.sessions import ClarificationSessionStore, get_session_store
from ai.types import (
    ClarificationQuestion,
    TranslateNeedsClarification,
    TranslateOk,
    TranslateOutcome,
)
from dsl.validate import validate_strategy
from exceptions import InvalidSignalError


class AITranslateError(Exception):
    """Base translation failure with a machine-readable code."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def translate_nl(
    text: str,
    *,
    provider: LLMProvider | None = None,
    store: ClarificationSessionStore | None = None,
) -> TranslateOutcome:
    """
    Translate natural language into a validated DSL strategy or clarification.

    Args:
        text: Free-text strategy description.
        provider: Optional provider override (defaults to ``get_provider()``).
        store: Optional session store override.

    Returns:
        ``TranslateOk`` or ``TranslateNeedsClarification``.

    Raises:
        AITranslateError: Empty text, bad JSON, invalid DSL, or provider failure.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        raise AITranslateError("EMPTY_TEXT", "Strategy text must not be empty")

    llm = provider or get_provider()
    session_store = store or get_session_store()
    system = build_system_prompt()
    user = build_user_prompt(cleaned)
    raw = _call_provider(llm, system, user)
    return _interpret_envelope(raw, original_text=cleaned, store=session_store)


def apply_clarification(
    session_id: str,
    answers: dict[str, str],
    *,
    provider: LLMProvider | None = None,
    store: ClarificationSessionStore | None = None,
) -> TranslateOutcome:
    """
    Apply clarification answers and re-run translation for a session.

    Args:
        session_id: Id returned from a prior ``needs_clarification`` response.
        answers: Map of question id → answer text.
        provider: Optional provider override.
        store: Optional session store override.

    Returns:
        ``TranslateOk`` or another ``TranslateNeedsClarification``.

    Raises:
        AITranslateError: Missing session, empty answers, or downstream failures.
    """
    if not answers:
        raise AITranslateError("EMPTY_ANSWERS", "Clarification answers must not be empty")

    session_store = store or get_session_store()
    session = session_store.update_answers(session_id, answers)
    if session is None:
        raise AITranslateError("SESSION_NOT_FOUND", f"Unknown or expired session: {session_id}")

    llm = provider or get_provider()
    system = build_system_prompt()
    user = build_user_prompt(
        session.text,
        prior_answers=session.answers,
        prior_questions=session.questions,
    )
    raw = _call_provider(llm, system, user)
    outcome = _interpret_envelope(
        raw,
        original_text=session.text,
        store=session_store,
        reuse_session_id=session.session_id,
    )
    if isinstance(outcome, TranslateOk):
        session_store.delete(session_id)
    return outcome


def _call_provider(llm: LLMProvider, system: str, user: str) -> str:
    """Invoke the provider and map HTTP failures."""
    try:
        return llm.complete(system, user)
    except ProviderHTTPError as exc:
        raise AITranslateError("PROVIDER_ERROR", str(exc)) from exc


def _interpret_envelope(
    raw: str,
    *,
    original_text: str,
    store: ClarificationSessionStore,
    reuse_session_id: str | None = None,
) -> TranslateOutcome:
    """Parse provider JSON, validate strategy, or create a clarification session."""
    payload = _parse_json_envelope(raw)
    status = payload.get("status")

    if status == "needs_clarification":
        questions_raw = payload.get("questions")
        if not isinstance(questions_raw, list) or not questions_raw:
            raise AITranslateError(
                "INVALID_LLM_JSON",
                "needs_clarification response missing questions",
            )
        questions = [_normalize_question(q) for q in questions_raw]
        question_dicts = [
            {"id": q.id, "prompt": q.prompt, "options": list(q.options)} for q in questions
        ]
        if reuse_session_id:
            session = store.get(reuse_session_id)
            if session is None:
                raise AITranslateError(
                    "SESSION_NOT_FOUND",
                    f"Unknown or expired session: {reuse_session_id}",
                )
            session.questions = question_dicts
            session.updated_at = time.time()
            session_id = reuse_session_id
        else:
            session = store.create(original_text, question_dicts)
            session_id = session.session_id
        return TranslateNeedsClarification(session_id=session_id, questions=questions)

    if status != "ok":
        raise AITranslateError(
            "INVALID_LLM_JSON",
            f"Unexpected status in LLM envelope: {status!r}",
        )

    strategy = payload.get("strategy")
    if not isinstance(strategy, dict):
        raise AITranslateError("INVALID_LLM_JSON", "ok response missing strategy object")

    try:
        model = validate_strategy(strategy)
    except InvalidSignalError as exc:
        raise AITranslateError("INVALID_DSL", str(exc)) from exc

    strategy_dict = model.model_dump(exclude_none=True)
    return TranslateOk(
        strategy=strategy_dict,
        explanation=explain_strategy(strategy_dict),
    )


def _parse_json_envelope(raw: str) -> dict[str, Any]:
    """Parse LLM text into a dict, stripping optional markdown fences."""
    text = raw.strip()
    fence = re.match(r"^```(?:json)?\s*([\s\S]*?)\s*```$", text)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AITranslateError("INVALID_LLM_JSON", f"LLM returned non-JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise AITranslateError("INVALID_LLM_JSON", "LLM JSON root must be an object")
    return data


def _normalize_question(raw: Any) -> ClarificationQuestion:
    """Coerce a question dict into ClarificationQuestion."""
    if not isinstance(raw, dict):
        raise AITranslateError("INVALID_LLM_JSON", "question must be an object")
    qid = str(raw.get("id") or "").strip()
    prompt = str(raw.get("prompt") or "").strip()
    if not qid or not prompt:
        raise AITranslateError("INVALID_LLM_JSON", "question requires id and prompt")
    options_raw = raw.get("options") or []
    if not isinstance(options_raw, list):
        raise AITranslateError("INVALID_LLM_JSON", "question options must be a list")
    options = [str(o) for o in options_raw]
    return ClarificationQuestion(id=qid, prompt=prompt, options=options)
