# Tech Design — BE Phase 7: Smart Money Concepts (SMC)

| Field | Value |
|---|---|
| **Status** | Ready for implementation (Agent B answers incorporated) |
| **PRD** | [prd.md](./prd.md) (Approved) |
| **Decisions** | D-96, D-97, D-98 |
| **HLD** | [PHASE_7_HLD.md](../../../backend/docs/PHASE_7_HLD.md) |
| **Agent D** | `smc/` library + tests + evaluator `"smc"` branch |
| **Agent E** | **Skipped** — no REST / no FE (Q11) |
| **Answers** | [answers.md](./answers.md) |

---

## 1. Architecture Overview

```
OHLCV DataFrame
        │
        ▼
┌───────────────────┐
│ structure.*       │  confirmed swings + trend (Phase 5)
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ smc detectors     │  BOS, CHOCH, FVG, OB, Sweep, Breaker, Mitigation
└─────────┬─────────┘
          ▼
   SmcResult (events + series helpers)
          │
          ▼
 signals/evaluator  ── if "smc" in condition → evaluate_smc_leg(...)
```

### Responsibilities

| Layer | Owns | Does not own |
|---|---|---|
| **`smc/`** | SMC math, config, named-condition Series | Pivots, indicators, HTTP |
| **`structure/`** | Swings / trend (unchanged) | SMC |
| **`signals/evaluator`** | Dispatch `"smc"` key | Concept algorithms |

---

## 2. Package layout

```
backend/
  smc/
    __init__.py
    types.py          # enums, events, SmcResult
    config.py         # SmcConfig defaults
    structure_view.py # confirmed swings usable at bar i
    bos.py            # BOS + CHOCH (shared state machine)
    fvg.py
    order_block.py
    liquidity.py
    breaker.py
    mitigation.py
    pipeline.py       # analyze_smc
    conditions.py     # evaluate_smc_leg
  tests/smc/
  docs/PHASE_7_HLD.md
```

### Touch outside package (minimal)

- `signals/types.py` — optional `smc`, `side` on `SignalCondition`
- `signals/evaluator.py` — `"smc"` branch in `_evaluate_condition`
- `docs/DECISIONS.md` — D-96–D-98; resolve OQ-19/20 in OPEN_QUESTIONS
- `docs/ROADMAP.md` — Phase 7 complete
- `docs/agents/PIPELINE_QUEUE.md`

### Do not modify

- `structure/**` (consume only)
- `indicators/registry.py`
- `patterns/**` (Phase 6)

---

## 3. Types & config

```python
class SmcSide(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"

class SmcConcept(StrEnum):
    BOS = "bos"
    CHOCH = "choch"
    FVG = "fvg"
    ORDER_BLOCK = "order_block"
    LIQUIDITY_SWEEP = "liquidity_sweep"
    BREAKER_BLOCK = "breaker_block"
    MITIGATION_BLOCK = "mitigation_block"

class FvgInvalidation(StrEnum):
    TOUCH = "touch"
    MIDPOINT = "midpoint"
    FULL_FILL = "full_fill"   # default D-97

@dataclass(frozen=True)
class SmcConfig:
    left_bars: int = 5
    right_bars: int = 5
    fvg_invalidation: FvgInvalidation = FvgInvalidation.FULL_FILL
    fvg_min_gap_pct: float = 0.0
    ob_use_wick_range: bool = False
    # ...

@dataclass(frozen=True)
class SmcEvent:
    concept: SmcConcept
    side: SmcSide
    index: int
    ts: pd.Timestamp
    price: float
    meta: dict  # concept-specific levels
```

---

## 4. Algorithms (ICT-leaning defaults)

### 4.1 Shared structure view

At bar `i`, `usable_swings(swings, i)` = confirmed swings with
`confirmation_index <= i`. Trend at `i` from `classify_trend` Series (already
confirmation-lagged).

### 4.2 BOS / CHOCH (`bos.py`)

Relevant level:

- Bullish break target = most recent usable swing **high** price
- Bearish break target = most recent usable swing **low** price

On bar `i` (need `close`):

- If `close[i] > last_swing_high` and trend[i] is **uptrend** → **bullish BOS**
- If `close[i] < last_swing_low` and trend[i] is **downtrend** → **bearish BOS**
- If `close[i] > last_swing_high` and trend[i] is **downtrend** → **bullish CHOCH**
- If `close[i] < last_swing_low` and trend[i] is **uptrend** → **bearish CHOCH**
- If trend is `range` / `undefined`: treat first close break as **CHOCH**; subsequent
  same-direction close breaks as **BOS** (local bias flip after CHOCH)

Each swing level triggers at most once (mark consumed after break).

### 4.3 FVG (`fvg.py`)

At bar `i >= 2`:

- Bullish: `high[i-2] < low[i]` → zone `(high[i-2], low[i])`
- Bearish: `low[i-2] > high[i]` → zone `(high[i], low[i-2])`

Skip if gap width / mid < `fvg_min_gap_pct`.

Invalidation from bar `i+1` onward:

| Mode | Bullish FVG invalidated when | Bearish when |
|---|---|---|
| `touch` | `low <= gap_top` (enters zone) | `high >= gap_bottom` |
| `midpoint` | `low <= mid` | `high >= mid` |
| `full_fill` | `low <= gap_bottom` | `high >= gap_top` |

Detection event on bar `i`; invalidation tracked in meta / separate events optional.
Named condition `fvg` fires on **formation** bar.

### 4.4 Order Block (`order_block.py`)

On bullish BOS at bar `b`: scan `b-1, b-2, ...` for last candle with `close < open`;
that bar is bullish OB. Zone body `[min(o,c), max(o,c)]` unless wick range enabled.
Mirror for bearish BOS (`close > open`).

Event index = OB candle index (formation known at BOS bar — store
`visible_from=b` in meta for no-lookahead consumers). Named condition fires at
**`visible_from`** (when OB is knowable), not the historical OB bar (avoids lookahead).

### 4.5 Liquidity Sweep (`liquidity.py`)

- Bearish sweep (highs): `high[i] > swing_high` and `close[i] < swing_high`
- Bullish sweep (lows): `low[i] < swing_low` and `close[i] > swing_low`

Swing must be usable at `i`. Each swing swept at most once.

### 4.6 Breaker Block (`breaker.py`)

After OB is visible: if close crosses through OB opposite side → breaker event on
that bar. Bullish OB broken down → bearish breaker; mirror opposite.

### 4.7 Mitigation Block (`mitigation.py`)

While OB valid (not broken): first bar where price overlaps OB zone
(`low <= zone_top and high >= zone_bottom`) → mitigation event.

---

## 5. Named conditions

```python
def evaluate_smc_leg(candles: pd.DataFrame, condition: dict) -> pd.Series:
    concept = condition["smc"]  # SmcConcept value
    side = condition.get("side", "any")
    params = condition.get("params", {})
    cfg = SmcConfig.from_params(params)
    result = analyze_smc(candles, cfg)
    series = result.series_for(concept)  # bool
    if side in ("bullish", "bearish"):
        series &= result.side_mask(concept, side)
    return series.fillna(False)
```

Evaluator:

```python
if "smc" in condition:
    from smc.conditions import evaluate_smc_leg
    return evaluate_smc_leg(candles, condition)
```

---

## 6. Testing plan

| File | Covers |
|---|---|
| `test_bos_choch.py` | With/against trend; confirmation lag; consume-once |
| `test_fvg.py` | Formation + three invalidation modes |
| `test_order_block.py` | OB from BOS; visible_from; body zone |
| `test_liquidity.py` | Wick sweep + close inside |
| `test_breaker_mitigation.py` | Break vs mitigate |
| `test_pipeline.py` | `analyze_smc` aggregation |
| `test_conditions.py` | Named legs + evaluator `"smc"` integration |

Synthetic OHLCV helpers (extend structure-style fixtures).

---

## 7. Docs / decisions

- Append **D-96** ICT defaults, **D-97** FVG `full_fill`, **D-98** library + `"smc"` conditions
- Mark OQ-19 / OQ-20 resolved in OPEN_QUESTIONS
- Write `PHASE_7_HLD.md`; mark ROADMAP Phase 7 Complete
