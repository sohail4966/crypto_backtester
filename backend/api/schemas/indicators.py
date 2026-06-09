"""
Indicator catalog and compute schemas.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class IndicatorCatalogEntry(BaseModel):
    """Registry metadata for one indicator key."""

    key: str
    inputs: list[str]
    shared_params: list[str] = Field(default_factory=list)
    default_params: dict[str, Any] = Field(default_factory=dict)
    pane: Literal["overlay", "subchart"] = "overlay"


class IndicatorSpec(BaseModel):
    """Indicator compute request item."""

    key: str
    params: dict[str, Any] = Field(default_factory=dict)
    pane: Literal["overlay", "subchart"] | None = None


class IndicatorPoint(BaseModel):
    """Single indicator value aligned to a bar timestamp."""

    time: int
    value: float | None


class IndicatorSeries(BaseModel):
    """Computed indicator series."""

    key: str
    params: dict[str, Any]
    pane: Literal["overlay", "subchart"]
    points: list[IndicatorPoint]


class IndicatorComputeRequest(BaseModel):
    """Batch indicator compute body."""

    symbol: str
    timeframe: str
    from_: int = Field(alias="from")
    to: int
    indicators: list[IndicatorSpec]

    model_config = {"populate_by_name": True}


class IndicatorComputeResponse(BaseModel):
    """Batch indicator compute result."""

    symbol: str
    timeframe: str
    series: list[IndicatorSeries]
