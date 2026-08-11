# Tech Design — BE Phase 6: Pattern Recognition

| Field | Value |
|---|---|
| **Status** | Ready for implementation (Agent B answers incorporated) |
| **PRD** | [prd.md](./prd.md) (Approved) |
| **Decisions** | D-99 (refs), D-100 (binary + confidence), D-101 (completed-only); D-11, D-61, D-62 |
| **HLD** | [PHASE_6_HLD.md](../../../backend/docs/PHASE_6_HLD.md) |
| **Agent D** | `patterns/` library + tests |
| **Agent E** | **Skipped** — no REST / no FE (Q13) |
| **Answers** | [answers.md](./answers.md) |

---

## 1. Architecture Overview

```
OHLCV DataFrame
        │
        ├──────────────────────────────┐
        ▼                              ▼
┌───────────────────┐         ┌────────────────────┐
│ detect_candles    │         │ analyze_structure  │  confirmed_only=True
│ (OHLC geometry)   │         │ (Phase 5 swings)   │
└─────────┬─────────┘         └─────────┬──────────┘
          │                             │
          │                   ┌─────────┴──────────┐
          │                   ▼                    ▼
          │         ┌─────────────────┐  ┌──────────────────┐
          │         │ detect_classical│  │ detect_divergence│
          │         │ (swing geometry)│  │ + RSI/MACD/Stoch │
          │         └────────┬────────┘  └────────┬─────────┘
          │                  │                    │
          └────────┬─────────┴────────────────────┘
                   ▼
          PatternHit list → boolean Series dict (sparse on end_index)
                   ▼
              PatternResult
```

### Responsibilities

| Layer | Owns | Does not own |
|---|---|---|
| **`patterns/`** | Candle / classical / divergence rules; Series packing | Pivot math, indicator formulas, HTTP |
| **`structure/`** | Swings (imported) | Pattern geometry |
| **`indicators/`** | RSI / MACD_HIST / STOCH_K | Divergence logic |
| **`signals/evaluator.py`** | Unchanged in Phase 6 | Pattern YAML |

---

## 2. Package layout

```
backend/
  patterns/
    __init__.py
    types.py           # PatternName, PatternFamily, PatternHit, PatternResult
    candles.py         # 5a
    classical.py       # 5b
    divergence.py      # 5c
    series.py          # hits_to_signals
    pipeline.py        # analyze_patterns
  tests/patterns/
    helpers.py
    test_candles.py
    test_classical.py
    test_divergence.py
    test_pipeline.py
  docs/PHASE_6_HLD.md
```

### Do not modify

- `signals/evaluator.py` (no `pattern:` hook)
- `indicators/**` (import only)
- API routers / OpenAPI (no Phase 6 REST)

---

## 3. Types

```python
class PatternFamily(StrEnum):
    CANDLE = "candle"
    CLASSICAL = "classical"
    DIVERGENCE = "divergence"

class PatternName(StrEnum):
    # 5a
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
    # 5b
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
    # 5c
    RSI_REGULAR_BULLISH = "rsi_regular_bullish"
    RSI_REGULAR_BEARISH = "rsi_regular_bearish"
    RSI_HIDDEN_BULLISH = "rsi_hidden_bullish"
    RSI_HIDDEN_BEARISH = "rsi_hidden_bearish"
    MACD_REGULAR_BULLISH = "macd_regular_bullish"
    ...
    STOCH_REGULAR_BULLISH = "stoch_regular_bullish"
    ...

@dataclass(frozen=True)
class PatternHit:
    name: PatternName
    family: PatternFamily
    direction: Literal["bullish", "bearish"]
    start_index: int
    end_index: int
    start_ts: pd.Timestamp
    end_ts: pd.Timestamp
    confidence: float
    levels: dict[str, float]

@dataclass(frozen=True)
class PatternResult:
    hits: list[PatternHit]
    signals: dict[str, pd.Series]  # name -> bool Series
```

---

## 4. Algorithms (summary)

### 4.1 Candles — geometry constants

| Constant | Default | Use |
|---|---|---|
| `DOJI_BODY_MAX_RATIO` | 0.1 | Doji body / range |
| `HAMMER_LOWER_WICK_MIN` | 2.0 | Lower wick / body |
| `HAMMER_UPPER_WICK_MAX` | 0.5 | Upper wick / body |
| `ENGULF_MIN_BODY_RATIO` | 1.0 | Current body covers prior |

Emit hit at last candle of the pattern (2-bar or 3-bar).

### 4.2 Classical — swing rules

- Input: confirmed `SwingPoint` list + full OHLC for breakout close check.
- Double top: two highs within `CLASSICAL_EQ_TOLERANCE_PCT`, intervening low, close below that low.
- H&S: left shoulder / head / right shoulder highs; neckline from intervening lows; close below neckline.
- Triangles: last 3+ alternating swings with converging bound slopes; close beyond flat/sloped bound.
- Flag: impulse ≥ 3%, then 2–4 swing consolidation channel against impulse; close in impulse direction.
- Pennant: impulse + converging consolidation.
- Wedge: both bounds slope same direction and converge; breakout opposite the wedge bias (rising→bearish).
- Cup & handle: three lows forming U (rim, cup low, rim) + shallow handle high/low; close above right rim.

Breakout look-ahead: `BREAKOUT_LOOKAHEAD_BARS = 20` after structure complete.

### 4.3 Divergence

- Take last two confirmed highs (bearish) or lows (bullish).
- Compare price direction vs oscillator sampled at those indices.
- Regular bearish: price HH, osc LH. Regular bullish: price LL, osc HL.
- Hidden bullish: price HL, osc LL. Hidden bearish: price LH, osc HH.
- Oscillators: `rsi`, `macd_histogram`, `stoch_k` from `indicators.talib_wrappers`.
- Confirmation bar = index of the later swing’s confirmation (or the later swing bar if already confirmed).

### 4.4 Series packing

```python
def hits_to_signals(hits, index) -> dict[str, pd.Series]:
    # False-filled Series per name; set True at end_index
```

---

## 5. Pipeline

```python
def analyze_patterns(
    df,
    *,
    families=("candle", "classical", "divergence"),
    left_bars=5,
    right_bars=5,
    tolerance_pct=0.0015,
    ...
) -> PatternResult
```

---

## 6. Testing strategy

- Synthetic OHLCV builders in `tests/patterns/helpers.py`.
- One fixture per major pattern asserting hit name, direction, and Series True at end.
- Empty / short series → empty hits, empty or all-False signals.
- Classical tests construct explicit swing-friendly high/low paths.

---

## 7. Agent E

**Skipped** — no HTTP surface (Q13).
