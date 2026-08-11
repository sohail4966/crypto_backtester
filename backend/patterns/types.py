"""
Pattern recognition types: names, hits, and aggregate results.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

import pandas as pd

PatternDirection = Literal["bullish", "bearish"]


class PatternFamily(StrEnum):
    """Pattern category (ROADMAP 5a / 5b / 5c)."""

    CANDLE = "candle"
    CLASSICAL = "classical"
    DIVERGENCE = "divergence"


class PatternName(StrEnum):
    """Canonical pattern signal keys (flat names for Series dict)."""

    # 5a — candlesticks
    BULLISH_ENGULFING = "bullish_engulfing"
    BEARISH_ENGULFING = "bearish_engulfing"
    HAMMER = "hammer"
    INVERTED_HAMMER = "inverted_hammer"
    SHOOTING_STAR = "shooting_star"
    DOJI = "doji"
    GRAVESTONE_DOJI = "gravestone_doji"
    DRAGONFLY_DOJI = "dragonfly_doji"
    MORNING_STAR = "morning_star"
    EVENING_STAR = "evening_star"
    THREE_WHITE_SOLDIERS = "three_white_soldiers"
    THREE_BLACK_CROWS = "three_black_crows"
    BULLISH_HARAMI = "bullish_harami"
    BEARISH_HARAMI = "bearish_harami"

    # 5b — classical
    DOUBLE_TOP = "double_top"
    DOUBLE_BOTTOM = "double_bottom"
    HEAD_AND_SHOULDERS = "head_and_shoulders"
    INV_HEAD_AND_SHOULDERS = "inv_head_and_shoulders"
    ASC_TRIANGLE = "ascending_triangle"
    DESC_TRIANGLE = "descending_triangle"
    SYM_TRIANGLE = "symmetrical_triangle"
    BULL_FLAG = "bull_flag"
    BEAR_FLAG = "bear_flag"
    PENNANT = "pennant"
    RISING_WEDGE = "rising_wedge"
    FALLING_WEDGE = "falling_wedge"
    CUP_AND_HANDLE = "cup_and_handle"

    # 5c — divergence
    RSI_REGULAR_BULLISH = "rsi_regular_bullish"
    RSI_REGULAR_BEARISH = "rsi_regular_bearish"
    RSI_HIDDEN_BULLISH = "rsi_hidden_bullish"
    RSI_HIDDEN_BEARISH = "rsi_hidden_bearish"
    MACD_REGULAR_BULLISH = "macd_regular_bullish"
    MACD_REGULAR_BEARISH = "macd_regular_bearish"
    MACD_HIDDEN_BULLISH = "macd_hidden_bullish"
    MACD_HIDDEN_BEARISH = "macd_hidden_bearish"
    STOCH_REGULAR_BULLISH = "stoch_regular_bullish"
    STOCH_REGULAR_BEARISH = "stoch_regular_bearish"
    STOCH_HIDDEN_BULLISH = "stoch_hidden_bullish"
    STOCH_HIDDEN_BEARISH = "stoch_hidden_bearish"


@dataclass(frozen=True)
class PatternHit:
    """
    A single completed pattern detection.

    ``end_index`` is the confirmation bar (Series True slot). ``confidence`` is a
    0–1 quality heuristic (D-100); it does not gate emission by default.
    """

    name: PatternName
    family: PatternFamily
    direction: PatternDirection
    start_index: int
    end_index: int
    start_ts: pd.Timestamp
    end_ts: pd.Timestamp
    confidence: float
    levels: dict[str, float]


@dataclass(frozen=True)
class PatternResult:
    """Aggregate pattern analysis: hit list plus sparse boolean Series per name."""

    hits: list[PatternHit]
    signals: dict[str, pd.Series]
