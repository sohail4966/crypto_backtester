"""
Named strategy file library (Phase 9 — simple JSON store).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from dsl.validate import validate_strategy
from exceptions import InvalidSignalError

_DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "data" / "strategies"
_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def default_library_root() -> Path:
    """Return the default strategies directory."""
    return _DEFAULT_ROOT


def _resolve_root(root: Path | None) -> Path:
    path = Path(root) if root is not None else default_library_root()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_name(name: str) -> str:
    if not _SAFE_NAME.match(name):
        raise InvalidSignalError(
            f"Invalid strategy name {name!r}; use alphanumerics, dot, underscore, hyphen"
        )
    return name


def strategy_path(name: str, *, root: Path | None = None) -> Path:
    """Return the JSON path for a named strategy."""
    return _resolve_root(root) / f"{_safe_name(name)}.json"


def save_strategy(name: str, strategy: dict[str, Any], *, root: Path | None = None) -> Path:
    """
    Validate and persist a named strategy as JSON.

    Args:
        name: Library key.
        strategy: Strategy document.
        root: Optional library directory.

    Returns:
        Path written.
    """
    model = validate_strategy(strategy)
    path = strategy_path(name, root=root)
    path.write_text(model.model_dump_json(indent=2, exclude_none=True) + "\n", encoding="utf-8")
    return path


def load_strategy(name: str, *, root: Path | None = None) -> dict[str, Any]:
    """
    Load and validate a named strategy.

    Args:
        name: Library key.
        root: Optional library directory.

    Returns:
        Strategy dict.
    """
    path = strategy_path(name, root=root)
    if not path.is_file():
        raise FileNotFoundError(f"Strategy not found: {name}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise InvalidSignalError("Strategy file must contain a JSON object")
    return validate_strategy(raw).model_dump(exclude_none=True)


def list_strategies(*, root: Path | None = None) -> list[str]:
    """Return sorted strategy names in the library."""
    directory = _resolve_root(root)
    return sorted(p.stem for p in directory.glob("*.json") if p.is_file())


def delete_strategy(name: str, *, root: Path | None = None) -> None:
    """Remove a named strategy file if it exists."""
    path = strategy_path(name, root=root)
    if path.is_file():
        path.unlink()
