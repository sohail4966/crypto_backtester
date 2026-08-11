"""
Tests for named strategy file library.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dsl import list_strategies, load_strategy, save_strategy
from exceptions import InvalidSignalError


def _strategy() -> dict:
    return {
        "schema_version": "1",
        "entry": {"indicator": "RSI", "params": {"period": 14}, "op": "<", "value": 30},
        "exit": {"indicator": "RSI", "params": {"period": 14}, "op": ">", "value": 70},
    }


def test_save_load_list_roundtrip(tmp_path: Path) -> None:
    path = save_strategy("rsi_oversold", _strategy(), root=tmp_path)
    assert path.is_file()
    loaded = load_strategy("rsi_oversold", root=tmp_path)
    assert loaded["schema_version"] == "1"
    assert loaded["entry"]["indicator"] == "RSI"
    assert "rsi_oversold" in list_strategies(root=tmp_path)


def test_invalid_name_rejected(tmp_path: Path) -> None:
    with pytest.raises(InvalidSignalError, match="Invalid strategy name"):
        save_strategy("../evil", _strategy(), root=tmp_path)
