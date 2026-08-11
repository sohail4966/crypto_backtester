# Phase 5 High Level Design — Market Structure Detection

**Status:** Complete — see [Phase 5 Completion Assessment](#phase-5-completion-assessment)  
**Prerequisite:** Phase 2 complete (indicators); Phase 1 `get_candles()` data boundary  
**Decisions:** D-53–D-66, D-59, D-61, D-63, D-75  
**Agent artifacts:** [docs/agents/be-phase-5-structure/](../../docs/agents/be-phase-5-structure/)  
**Next phase after this:** [Phase 6 — Pattern Recognition](ROADMAP.md#phase-6--pattern-recognition)

---

## Starting Point

The platform can load OHLCV and compute indicators, but has no shared swing / structure
layer. Session `PIVOT_*` indicators are floor/ceiling reference levels — **not** swing
structure. Patterns and SMC must not invent competing pivot definitions.

**Phase 5 goal:** Given a candle series, reliably detect swing highs/lows, label
HH/HL/LH/LL/EQH/EQL, derive discrete S/R, classify trend from confirmed structure, and
expose multi-timeframe context via forward-fill.

---

## Done Criteria

1. `structure/` package implements pivot 5/5 swings (confirmed + provisional).
2. Labels follow D-65; EQ tolerance default 0.15% (D-55).
3. `StructureLevels` recency-first, `k=3` (D-57, D-64).
4. `classify_trend` event-driven + forward-filled (D-56, D-66).
5. `StructureContext` loads base + up to two HTF via `get_candles`, as-of ffill (D-58).
6. No evaluator YAML hook; not registered in `indicators/` (D-59, D-63).
7. Unit tests under `tests/structure/`; `run_structure_report.py` for manual review (D-60).
8. ROADMAP Phase 5 marked complete.

---

## Architecture

```
structure/
  types.py       SwingKind, SwingLabel, Trend, SwingPoint, StructureLevels, StructureResult
  swings.py      detect_swings
  labels.py      label_swings
  levels.py      structure_levels
  trend.py       classify_trend
  pipeline.py    analyze_structure
  context.py     StructureContext
```

Library-first. Optional REST deferred. ZigZag and similarity search out of scope
(D-54, D-61).

### Data flow

1. Normalize OHLCV → DatetimeIndex on `ts` (UTC).
2. Detect pivots on `high` / `low` with strict inequalities.
3. Label chronologically within kind.
4. Build S/R from confirmed swings.
5. Emit trend Series at confirmation events; ffill.
6. Multi-TF: repeat per frame; map HTF trend onto base index with `ffill` as-of join.

---

## Key contracts

| Contract | Rule |
|---|---|
| Pivot defaults | `left_bars=5`, `right_bars=5` |
| Confirmation | Bar `i` confirms at index `i + right_bars` |
| Prices | High swings use `high`; low swings use `low` |
| Equality | `abs(a-b)/mid <= 0.0015` → EQH/EQL |
| Trend up | Latest high label HH **and** latest low label HL |
| Trend down | LH **and** LL |
| Trend range | EQH/EQL on latest side **or** mixed directions |
| Trend undefined | < 2 confirmed highs or < 2 confirmed lows |
| Backtest default | `confirmed_only=True` when filtering for consumers |
| HTF | No lookahead: `htf_ts <= base_ts` |

---

## Validation

- Synthetic unit tests (deterministic).
- Manual: `run_structure_report.py` on BTC/USDT across regimes (D-60).
- No TradingView parity gate.

---

## Out of scope

| Item | Phase |
|---|---|
| Classical / candle patterns | 6 |
| SMC (BOS, FVG, OB) | 7 |
| `structure:` signal DSL | 6+ / 9 |
| Chart REST overlays | Later |
| ZigZag / similarity | Deferred (D-54, D-61) |

---

## Implementation steps

1. Types + swing detection + tests.
2. Labels + levels + trend + tests.
3. `analyze_structure` pipeline.
4. `StructureContext` + tests.
5. Report script.
6. ROADMAP + completion assessment.

---

## Phase 5 Completion Assessment

Phase 5 delivers a **library-only** market structure package under `structure/`:
symmetric pivot swings, structural labels (incl. EQH/EQL), recency-first S/R, event-driven
trend with forward-fill, and multi-TF `StructureContext` via `get_candles()`.

### Evidence checked

| Check | Result | Notes |
|---|---|---|
| `structure/` package | Done | types, swings, labels, levels, trend, pipeline, context, ohlcv |
| Unit suite | Passing | `pytest tests/structure/` → **17 passed** |
| Report script | Done | `run_structure_report.py` CSV + JSON summary |
| No evaluator hook | Done | `signals/evaluator.py` untouched (D-63) |
| Not in indicators registry | Done | Separate package (D-59) |
| No REST | Done | Deferred per D-63 / Agent B Q9 |
| HLD + agent A–H | Done | `docs/agents/be-phase-5-structure/` |

### Rating breakdown

| Area | Score | Comment |
|---|---|---|
| Architecture alignment | 9/10 | Matches D-53–D-66; clean separation from indicators |
| Algorithm correctness | 8.5/10 | Locked by synthetic tests; manual chart review still recommended |
| Test coverage | 8.5/10 | Pivots, labels, EQ, levels, trend, context as-of ffill |
| Documentation | 9/10 | PHASE_5_HLD, ROADMAP, PRD/tech-design/answers |
| Scope discipline | 9.5/10 | Library-only; no ZigZag, similarity, REST, or YAML hook |

### Known gaps (acceptable for Phase 5)

- **Manual visual validation** on live BTC/USDT still recommended via report script (D-60).
- **No REST / chart overlay** — Phase 6+ or a later API thin layer if needed.
- **No forced high/low alternation** — consecutive same-kind swings allowed (Agent B Q13).

### Completion verdict

Phase 5 is **complete**. Phase 6 pattern recognition can import `structure` and build on
confirmed swings without inventing a competing pivot definition.
