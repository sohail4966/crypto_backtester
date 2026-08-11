# PRD — BE Phase 7: Smart Money Concepts (SMC)

| Field | Value |
|---|---|
| **Status** | Approved (auto — no human-in-loop; product defaults below) |
| **Phase** | Backend Phase 7 |
| **Product intent** | [ROADMAP.md — Phase 7](../../../backend/docs/ROADMAP.md#phase-7--smart-money-concepts-smc) |
| **Prior contracts** | Phase 5 `structure/`; OQ-19 / OQ-20 (auto-resolved); D-53–D-66 |
| **Decisions** | D-96 (ICT-leaning defaults), D-97 (FVG invalidation), D-98 (library + named conditions) |

---

## 1. Problem / Goal

### Problem

Traders who use Smart Money Concepts need deterministic, auditable detectors for BOS,
CHOCH, FVG, Order Blocks, Liquidity Sweeps, Breaker Blocks, and Mitigation Blocks.
Definitions vary by educator; without a documented default and knobs, backtests are
irreproduceable and Phase 9 DSL cannot name these conditions.

### Goal

Ship a **`smc/` library** that, given OHLCV (+ Phase 5 swings/trend):

1. Detects each SMC concept with **ICT-leaning** documented interpretation defaults.
2. Exposes **configurable** parameters per detector.
3. Integrates as **named signal conditions** (`"smc": "<concept>"`) in the evaluator.
4. Remains **library-first** (no REST / no FE overlays in this phase).

Success: unit tests lock contracts; strategies can use e.g.
`{"smc": "bos", "side": "bullish"}` alongside indicator legs; Phase 6 patterns can
land in parallel without colliding on the `smc/` package.

---

## 2. User Roles

| Role | Description | Auth |
|---|---|---|
| **Library / DSL consumer** | Imports `smc` or uses `"smc"` conditions in strategy dicts. | N/A |
| **Developer / QA** | Runs `pytest tests/smc/` (+ evaluator SMC tests). | Local |
| **Chart client** | Not a Phase 7 consumer (no overlay API). | — |

---

## 3. Scope

### In scope (v1)

| Concept | Default interpretation (ICT-leaning) |
|---|---|
| **BOS** | Close beyond prior confirmed swing **in trend direction** |
| **CHOCH** | First close beyond prior confirmed swing **against** trend |
| **FVG** | 3-candle imbalance; invalidate on **full fill** (configurable) |
| **Order Block** | Last opposing candle before impulse that produces BOS |
| **Liquidity Sweep** | Wick beyond confirmed swing, close back inside |
| **Breaker Block** | Failed OB (close through) that flips role |
| **Mitigation Block** | Price returns into OB zone (partial fill / mitigate) |

Also: `SmcConfig`, `analyze_smc` pipeline, named-condition bridge, `PHASE_7_HLD.md`,
tests, ROADMAP update, A–H artifacts.

### Out of scope / deferred

| Item | Reason |
|---|---|
| REST `/smc` | Library-first (D-98) |
| FE overlays | Future FE |
| Mentfx / TTC as primary reference | OQ-19 → ICT-leaning (D-96) |
| Multi-position portfolio (D-43) | Unrelated; still deferred |
| Deep HTF SMC confluence API | May use `StructureContext` later |

### Parallelism note

Phase 6 patterns may edit `signals/` / `patterns/` concurrently. Phase 7 owns
`backend/smc/` + `tests/smc/` + phase docs. Evaluator change is a **small additive**
`"smc"` branch only (patterns should use `"pattern"` similarly).

---

## 4. UX / API Flows

### 4.1 Library

```
candles → analyze_smc(df, config?) → SmcResult
  (events per concept + boolean Series helpers)
```

### 4.2 Named signal condition

```yaml
entry:
  smc: bos
  side: bullish          # bullish | bearish | any
  params: {}             # optional SmcConfig overrides
```

Evaluator returns boolean Series (True on event bars); entry_trigger edge/level applies.

---

## 5. Acceptance Criteria

| ID | Criterion |
|---|---|
| **AC-1** | All seven concepts detectable with configurable params |
| **AC-2** | ICT-leaning defaults documented in HLD + module docstrings |
| **AC-3** | OQ-19 / OQ-20 resolved (D-96, D-97) |
| **AC-4** | Named `"smc"` conditions work in signal evaluator |
| **AC-5** | Uses Phase 5 confirmed swings; no competing pivot math |
| **AC-6** | `pytest tests/smc/` (+ evaluator SMC coverage) green |
| **AC-7** | No REST; package isolated under `smc/` |
| **AC-8** | PHASE_7_HLD + ROADMAP + A–H artifacts complete |

---

## 6. Non-goals / risks

- SMC is subjective; defaults are **one** interpretation — knobs are mandatory.
- False positives on noisy crypto are expected; thresholds are tunable.
- Visual BTC/USDT chart review recommended but not blocking for library CI.
