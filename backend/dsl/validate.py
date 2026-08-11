"""
Validate strategy dicts against the Trading DSL.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError as PydanticValidationError

from dsl.schema import StrategyModel
from exceptions import InvalidSignalError


def validate_strategy(strategy: dict[str, Any]) -> StrategyModel:
    """
    Validate a strategy dict and return the parsed pydantic model.

    Missing ``schema_version`` defaults to ``\"1\"``.

    Args:
        strategy: Raw strategy mapping (YAML/JSON loaded).

    Returns:
        Parsed ``StrategyModel``.

    Raises:
        InvalidSignalError: If the document fails schema or semantic checks.
    """
    payload = dict(strategy)
    payload.setdefault("schema_version", "1")
    try:
        return StrategyModel.model_validate(payload)
    except PydanticValidationError as exc:
        raise InvalidSignalError(_format_pydantic_error(exc)) from exc


def _format_pydantic_error(exc: PydanticValidationError) -> str:
    """Collapse pydantic errors into a single InvalidSignalError message."""
    parts: list[str] = []
    for err in exc.errors():
        loc = ".".join(str(x) for x in err.get("loc", ()))
        msg = err.get("msg", "invalid")
        parts.append(f"{loc}: {msg}" if loc else msg)
    return "; ".join(parts) if parts else "Invalid strategy"
