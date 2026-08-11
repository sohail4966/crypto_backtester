# Phase 7 High Level Design — Smart Money Concepts (SMC)

**Status:** Complete — see [Phase 7 Completion Assessment](#phase-7-completion-assessment)  
**Prerequisite:** Phase 5 `structure/` (confirmed swings + trend)  
**Decisions:** D-96 (ICT-leaning defaults), D-97 (FVG invalidation), D-98 (library + named conditions)  
**Agent artifacts:** [docs/agents/be-phase-7-smc/](../../docs/agents/be-phase-7-smc/)  
**Parallel note:** Phase 6 `patterns/` may land concurrently — Phase 7 owns `smc/` only
(+ minimal `"smc"` evaluator branch).

---

## Starting Point

Phase 5 provides pivot swings, HH/HL labeling, and trend. Traders who use Smart Money
Concepts still need BOS, CHOCH, FVG, Order Blocks, Liquidity Sweeps, Breaker Blocks,
and Mitigation Blocks. Those definitions are subjective; this phase ships **one
ICT-leaning interpretation** with knobs.

**Phase 7 goal:** Configurable SMC detectors as a library, integrated as named
signal conditions (`"smc": "<concept>"`).

---

## Done Criteria

1. All seven concepts detectable under `smc/`.
2. ICT-leaning defaults documented; parameters overridable via `SmcConfig` / condition `params`.
3. OQ-19 / OQ-20 resolved (D-96, D-97).
4. Named `"smc"` conditions evaluate in `signals/evaluator.py`.
5. Uses Phase 5 confirmed swings only (no second pivot engine).
6. `pytest tests/smc/` green.
7. No REST / no FE overlays.
8. ROADMAP Phase 7 marked complete; A–H artifacts present.

---

## Architecture

```
smc/
  types.py           SmcConcept, SmcSide, SmcEvent, SmcResult, FvgInvalidation
  config.py          SmcConfig (ICT-leaning defaults)
  structure_view.py  usable swings at bar i (no lookahead)
  bos.py             BOS + CHOCH
  fvg.py             Fair Value Gaps + invalidation
  order_block.py     Order Blocks from BOS
  liquidity.py       Liquidity sweeps
  breaker.py         Breaker blocks
  mitigation.py      Mitigation blocks
  pipeline.py        analyze_smc
  conditions.py      evaluate_smc_leg
```

### Data flow

1. Normalize OHLCV → Phase 5 `analyze_structure(confirmed_only=True)`.
2. Detect BOS/CHOCH from close breaks of usable swings vs trend bias.
3. Detect FVGs (3-candle imbalance); track invalidation per D-97 mode.
4. Derive OBs from BOS (event visible at BOS bar).
5. Sweeps, breakers, mitigations from swings / OB zones.
6. Named condition → boolean Series on event bars.

### Named condition shape

```yaml
entry:
  smc: bos                 # bos|choch|fvg|order_block|liquidity_sweep|breaker_block|mitigation_block
  side: bullish            # bullish|bearish|any
  params:
    left_bars: 5
    right_bars: 5
    fvg_invalidation: full_fill
```

---

## ICT-leaning interpretation defaults

| Concept | Default rule |
|---|---|
| **BOS** | Close beyond confirmed swing **with** structure trend |
| **CHOCH** | Close beyond confirmed swing **against** trend (or first break in range) |
| **FVG** | 3-candle gap; invalidate on **full_fill** (through far edge) |
| **Order Block** | Last opposing **body** candle before BOS; signal at BOS bar |
| **Liquidity Sweep** | Wick beyond swing + close back inside (same bar) |
| **Breaker** | Close through OB invalidating side → flipped-role event |
| **Mitigation** | First return into OB zone while still valid |

---

## Key contracts

| Contract | Rule |
|---|---|
| Pivot source | Phase 5 only |
| Usable swing | `confirmation_index <= bar` |
| BOS/CHOCH break | **Close**, not wick-only |
| FVG default | `full_fill` (D-97); `touch` / `midpoint` optional |
| OB visibility | Event index = BOS bar (`visible_from`) |
| Signal Series | True on **event bars** only |
| Registry | Not added to `indicators/registry.py` |

---

## Validation

```bash
cd backend && .venv/bin/pytest tests/smc/ -v
```

---

## Phase 7 Completion Assessment

| Criterion | Status | Evidence |
|---|---|---|
| Seven detectors | Done | `smc/*.py` |
| Configurable + documented ICT defaults | Done | `SmcConfig`, this HLD |
| OQ-19 / OQ-20 | Done | D-96, D-97 |
| Named evaluator conditions | Done | `"smc"` branch + `test_pipeline.py` |
| Structure coupling | Done | `structure_view.py` |
| Tests | Done | `tests/smc/` (12 passed) |
| Library-first (no REST) | Done | package only |
| Docs / ROADMAP / A–H | Done | this file + agent folder |

**Verdict:** Phase 7 is **complete**.
