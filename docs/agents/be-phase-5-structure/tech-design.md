# Tech Design — BE Phase 5: Market Structure Detection

| Field | Value |
|---|---|
| **Status** | Ready for implementation (Agent B answers incorporated) |
| **PRD** | [prd.md](./prd.md) (Approved) |
| **Decisions** | D-53–D-66, D-59, D-61, D-63 |
| **HLD** | [PHASE_5_HLD.md](../../../backend/docs/PHASE_5_HLD.md) |
| **Agent D** | `structure/` library + tests + `run_structure_report.py` |
| **Agent E** | **Skipped** — no REST / no FE (Q9) |
| **Answers** | [answers.md](./answers.md) |

---

## 1. Architecture Overview

```
OHLCV DataFrame (ts, open, high, low, close, volume)
        │
        ▼
┌───────────────────┐
│ detect_swings     │  pivot 5/5 → SwingPoint list (confirmed + provisional)
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ label_swings      │  FIRST / HH / HL / LH / LL / EQH / EQL
└─────────┬─────────┘
          ▼
┌───────────────────┐     ┌────────────────────┐
│ structure_levels  │     │ classify_trend     │  event-driven Series
│ k=3, recency-first│     │ forward-fill       │
└───────────────────┘     └────────────────────┘
          │
          ▼
   StructureResult (single TF)

StructureContext.load / from_frames
  → per-TF StructureResult
  → HTF trend as-of forward-fill onto base index
```

### Responsibilities

| Layer | Owns | Does not own |
|---|---|---|
| **`structure/`** | Pivots, labels, S/R, trend, multi-TF context | Indicators registry, YAML signals, HTTP |
| **`run_structure_report.py`** | CLI load + export | Chart rendering |
| **`get_candles`** | DB reads for context/report | Structure math |

---

## 2. Package layout

```
backend/
  structure/
    __init__.py          # public exports
    types.py             # enums + dataclasses
    swings.py            # detect_swings
    labels.py            # label_swings + equal tolerance
    levels.py            # structure_levels
    trend.py             # classify_trend
    pipeline.py          # analyze_structure
    context.py           # StructureContext
  run_structure_report.py
  tests/structure/
    test_swings.py
    test_labels.py
    test_levels.py
    test_trend.py
    test_pipeline.py
    test_context.py
  docs/PHASE_5_HLD.md
```

### Do not modify

- `indicators/**` (except docs cross-links if needed)
- `signals/evaluator.py` (no `structure:` hook)
- API routers / OpenAPI (no Phase 5 REST)

---

## 3. Types

```python
class SwingKind(StrEnum):
    HIGH = "high"
    LOW = "low"

class SwingLabel(StrEnum):
    FIRST = "first"
    HH = "HH"
    HL = "HL"
    LH = "LH"
    LL = "LL"
    EQH = "EQH"
    EQL = "EQL"

class Trend(StrEnum):
    UPTREND = "uptrend"
    DOWNTREND = "downtrend"
    RANGE = "range"
    UNDEFINED = "undefined"

@dataclass(frozen=True)
class SwingPoint:
    index: int              # bar index in source frame
    ts: pd.Timestamp
    price: float
    kind: SwingKind
    label: SwingLabel
    confirmed: bool
    confirmation_index: int | None  # i + right_bars when confirmed

@dataclass(frozen=True)
class StructureLevels:
    support: list[float]      # recent swing lows, [0] = most recent
    resistance: list[float]   # recent swing highs, [0] = most recent

@dataclass(frozen=True)
class StructureResult:
    swings: list[SwingPoint]
    levels: StructureLevels
    trend: pd.Series          # Trend values, DatetimeIndex from ts
```

Defaults: `DEFAULT_LEFT_BARS = 5`, `DEFAULT_RIGHT_BARS = 5`,
`DEFAULT_EQ_TOLERANCE_PCT = 0.0015`, `DEFAULT_LEVEL_COUNT = 3`.

---

## 4. Algorithms

### 4.1 `detect_swings(df, left_bars=5, right_bars=5, confirmed_only=False)`

For each candidate index `i` in `[left_bars, n)`:

**Confirmed** (`i + right_bars < n`):

- High: `high[i] > max(high[i-left:i])` and `high[i] > max(high[i+1:i+right+1])` (strict vs each neighbor equivalently).
- Low: mirror on `low` with `<`.

Set `confirmed=True`, `confirmation_index = i + right_bars`.

**Provisional** (`i > n - 1 - right_bars` and not yet confirmable):

- Left window complete; compare against all available right bars `high[i+1:n]` (may be empty only at last bar — still OK if left extreme).
- `confirmed=False`, `confirmation_index=None`.

Labels initially `FIRST` placeholder; `label_swings` overwrites.

When `confirmed_only=True`, filter to confirmed.

### 4.2 `label_swings(swings, tolerance_pct=0.0015)`

Process in time order. For each swing vs prior **same kind**:

1. `abs(a-b) / mid <= tolerance` → EQH / EQL (`mid = (a+b)/2`, guard mid>0)
2. Else higher → HH (high) / HL (low)
3. Else lower → LH / LL
4. No prior → FIRST

Return new list (frozen dataclasses replaced).

### 4.3 `structure_levels(swings, k=3)`

From **confirmed** swings only: last `k` lows → `support`, last `k` highs → `resistance`,
most-recent-first.

### 4.4 `classify_trend(df, swings) -> pd.Series`

1. Build event map: at each **confirmed** swing’s `confirmation_index` timestamp, recompute state from labels of latest confirmed high + latest confirmed low among swings whose confirmation_index ≤ current event.
2. Rules (Q2/Q3): need ≥1 labeled high with a prior high (i.e. latest high label ≠ FIRST alone insufficient — need two highs and two lows ⇒ latest labels not FIRST for both kinds… actually FIRST means only one of that kind so far → `undefined`). So: if fewer than 2 confirmed highs or 2 confirmed lows → `undefined`. Else apply HH+HL / LH+LL / else range.
3. Forward-fill event states onto full `ts` index; leading bars before first event = `undefined`.

### 4.5 `analyze_structure(df, **params) -> StructureResult`

Orchestrates detect → label → levels → trend.

### 4.6 `StructureContext`

```python
@dataclass
class StructureContext:
    base_tf: str
    base: StructureResult
    higher: dict[str, StructureResult]   # tf → result
    htf_trend_on_base: dict[str, pd.Series]

    @classmethod
    def from_frames(...)
    @classmethod
    def load(cls, symbol, base_tf, htf_tfs, start, end, **params)
```

HTF join: `series.reindex(base_index, method="ffill")` after ensuring HTF trend index is sorted unique `ts`. Empty TF → `ValueError`.

---

## 5. Report script

`run_structure_report.py`:

- Args: `--symbol`, `--timeframe`, `--start`, `--end`, optional `--htf` (repeatable), `--output-dir`.
- Loads via `get_candles` / `StructureContext.load`.
- Writes `output/structure_{symbol}_{tf}_swings.csv` (ts, price, kind, label, confirmed).
- Optional JSON summary: levels + trend value counts.

---

## 6. Testing plan

| Area | Cases |
|---|---|
| Pivots | Synthetic clear swing; plateau non-pivot; confirmation lag; provisional at tip |
| Labels | HH/HL/LH/LL; EQ within/outside tolerance; FIRST |
| Levels | Order recency-first; k cap; ignore provisional |
| Trend | Uptrend/downtrend/range/undefined; forward-fill between events; EQ → range |
| Context | As-of ffill; no lookahead; empty HTF raises |
| Pipeline | End-to-end on synthetic OHLCV |

---

## 7. Agent E

**Out of scope.** No OpenAPI change, no FE.

---

## Gate

Design ready for Agent D.
