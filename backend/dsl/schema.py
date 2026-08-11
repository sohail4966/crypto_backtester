"""
Pydantic models for the Trading DSL (Phase 9).

Models are intentionally permissive on leaf keys so recursive JSON Schema export
remains LLM-friendly; semantic shape checks live in ``validate.py``.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from dsl.version import SCHEMA_VERSION, SUPPORTED_SCHEMA_VERSIONS

EntryTrigger = Literal["edge", "level"]
GroupOp = Literal["AND", "OR", "NOT", "SEQUENCE"]
CompareOp = Literal["<", "<=", ">", ">=", "=="]
OhlcvField = Literal["open", "high", "low", "close", "volume"]


class IndicatorRefModel(BaseModel):
    """Reference to another indicator series for cross-comparisons."""

    model_config = ConfigDict(extra="forbid")

    indicator: str
    params: dict[str, int | float | str] | None = None


class RefModel(BaseModel):
    """Right-hand side reference with optional lookback."""

    model_config = ConfigDict(extra="forbid")

    field: OhlcvField | None = None
    indicator: str | None = None
    params: dict[str, int | float | str] | None = None
    bars_ago: int = 0

    @model_validator(mode="after")
    def _one_source(self) -> RefModel:
        if (self.field is None) == (self.indicator is None):
            raise ValueError("ref requires exactly one of field or indicator")
        if self.bars_ago < 0:
            raise ValueError("bars_ago must be >= 0")
        return self


class ConditionModel(BaseModel):
    """
    Recursive condition node: group, sequence, or leaf.

    Discrimination is by keys (see tech-design Q3), not a single tag field.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    # Groups / sequence
    op: str | None = None
    conditions: list[ConditionModel] | None = None
    all: list[ConditionModel] | None = None
    any: list[ConditionModel] | None = None
    not_: ConditionModel | None = Field(default=None, alias="not")
    within_bars: int | None = None

    # Indicator / field leaves
    indicator: str | None = None
    field: OhlcvField | None = None
    value: float | None = None
    params: dict[str, int | float | str] | None = None
    compare: str | IndicatorRefModel | None = None
    ref: RefModel | None = None
    bars_ago: int | None = None
    timeframe: str | None = None

    # Named concept leaves
    smc: str | None = None
    side: str | None = None
    pattern: str | None = None

    @model_validator(mode="after")
    def _validate_shape(self) -> ConditionModel:
        group_keys = sum(
            [
                self.all is not None,
                self.any is not None,
                self.not_ is not None,
                self.op is not None and self.conditions is not None,
            ]
        )
        if group_keys > 1:
            raise ValueError("condition cannot mix all/any/not/op group forms")

        if self.all is not None:
            if not self.all:
                raise ValueError("'all' must contain at least one condition")
            return self

        if self.any is not None:
            if not self.any:
                raise ValueError("'any' must contain at least one condition")
            return self

        if self.not_ is not None:
            return self

        if self.op is not None:
            op = self.op.upper()
            if op not in {"AND", "OR", "NOT", "SEQUENCE"}:
                # Leaf comparison ops are handled below when indicator/field set.
                if self.indicator is not None or self.field is not None:
                    return self._validate_leaf()
                raise ValueError(f"Unknown group op: {self.op!r}")
            if not self.conditions:
                raise ValueError(f"{op} requires a non-empty conditions list")
            if op == "NOT" and len(self.conditions) != 1:
                raise ValueError("NOT requires exactly one child condition")
            if op == "SEQUENCE":
                if len(self.conditions) < 2:
                    raise ValueError("SEQUENCE requires at least two conditions")
                if self.within_bars is None or self.within_bars < 1:
                    raise ValueError("SEQUENCE requires within_bars >= 1")
            return self

        return self._validate_leaf()

    def _validate_leaf(self) -> ConditionModel:
        kinds = sum(
            [
                self.indicator is not None,
                self.field is not None,
                self.smc is not None,
                self.pattern is not None,
            ]
        )
        if kinds != 1:
            raise ValueError(
                "leaf condition requires exactly one of indicator, field, smc, pattern"
            )
        if self.bars_ago is not None and self.bars_ago < 0:
            raise ValueError("bars_ago must be >= 0")
        if self.smc is not None or self.pattern is not None:
            return self
        if self.op is None:
            raise ValueError("indicator/field leaf requires op")
        if self.op not in {"<", "<=", ">", ">=", "=="}:
            raise ValueError(f"Unknown comparison operator: {self.op!r}")
        if self.ref is None and self.compare is None and self.value is None:
            raise ValueError("leaf requires value, compare, or ref")
        if self.compare is not None and isinstance(self.compare, str):
            if self.compare != "close":
                raise ValueError("string compare must be 'close'")
        return self


class SideStrategyModel(BaseModel):
    """One side of a dual strategy."""

    model_config = ConfigDict(extra="allow")

    entry: ConditionModel
    exit: ConditionModel
    stop_loss: dict[str, Any] | None = None
    take_profit: dict[str, Any] | None = None
    sizing: dict[str, Any] | None = None


class StrategyModel(BaseModel):
    """Long-only or dual-side strategy document."""

    model_config = ConfigDict(extra="allow")

    schema_version: str = Field(default=SCHEMA_VERSION)
    entry_trigger: EntryTrigger = "edge"
    benchmark: str | None = None
    entry: ConditionModel | None = None
    exit: ConditionModel | None = None
    sizing: dict[str, Any] | None = None
    long: SideStrategyModel | None = None
    short: SideStrategyModel | None = None

    @model_validator(mode="after")
    def _shape_and_version(self) -> StrategyModel:
        if self.schema_version not in SUPPORTED_SCHEMA_VERSIONS:
            raise ValueError(
                f"Unsupported schema_version: {self.schema_version!r}. "
                f"Supported: {sorted(SUPPORTED_SCHEMA_VERSIONS)}"
            )
        dual = self.long is not None or self.short is not None
        mono = self.entry is not None or self.exit is not None
        if dual and mono:
            raise ValueError("strategy cannot mix long/short blocks with top-level entry/exit")
        if dual:
            if self.long is None or self.short is None:
                raise ValueError("dual strategy requires both long and short blocks")
            return self
        if self.entry is None or self.exit is None:
            raise ValueError("strategy requires entry and exit conditions")
        return self
