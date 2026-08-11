# Answers — BE Phase 9: Full Trading DSL (Agent B)

Decisive answers for [questions.md](./questions.md). Incorporated into [tech-design.md](./tech-design.md)
and [PHASE_9_HLD.md](../../../backend/docs/PHASE_9_HLD.md).

---

### Q1 → Answer

**Yes — Option A nested tree.** Groups use `op` ∈ {`AND`,`OR`,`NOT`} plus `conditions`.
`NOT` requires exactly one child. Recursive evaluation.

### Q2 → Answer

**Keep `all` as permanent AND alias** for backward compatibility. Prefer documenting
`op`/`conditions` as the canonical LLM form.

### Q3 → Answer

**Yes — key discrimination.** Evaluation order: group (`op`/`all`) → `SEQUENCE` →
`smc` → `pattern` → `field` / `indicator` leaf.

### Q4 → Answer

**Prefer supplied `frames` when present**; otherwise **resample** base OHLCV to the
requested HTF in-memory for library tests / callers without a DB. No DB fetch inside
the pure evaluator.

### Q5 → Answer

**Default: as-of forward-fill on HTF open labels (D-106)** — a base bar at `t` sees
the last HTF bar with `open <= t` (no future HTF opens). **Optional stricter mode:**
`align_series_to_base(..., completed_only=True)` delays availability until HTF close.

### Q6 → Answer

**Yes.** Missing/`None`/`== base_timeframe` → evaluate on base frame, no align.

### Q7 → Answer

**Yes.** RHS via `ref` with optional `bars_ago`. LHS may include `bars_ago` to shift
the left series. `bars_ago < 0` is invalid.

### Q8 → Answer

**Yes.** Keep `compare` as the cross-series path. Schema documents it for LLMs.

### Q9 → Answer

**Yes — pragmatic windowed order.** On bar `i` where last leg is True: require each
earlier leg `k` to have been True on some bar `j_k` with
`i - within_bars <= j_0 < j_1 < ... < j_{n-2} < i` (strictly increasing indices).

### Q10 → Answer

**2+ legs allowed** (`len(conditions) >= 2`). `within_bars` must be ≥ 1.

### Q11 → Answer

**`schema_version` string; default `"1"` when absent** so legacy strategies keep
working. Validators accept only known versions (`"1"` in v1).

### Q12 → Answer

**File JSON only** — no migration. Path configurable; default `data/strategies/`.

### Q13 → Answer

**Agent E skipped** — no REST in Phase 9.

### Q14 → Answer

**Yes.** `pattern` and `smc` are composable leaves inside any group/sequence.

### Q15 → Answer

**Yes.** Do not touch screener files. Document:
`from dsl import validate_strategy, strategy_json_schema` and
`from signals.evaluator import evaluate_signals`.

---

## Decisions to record

| ID | Summary |
|---|---|
| D-109 | Nested AND/OR/NOT tree + schema_version; Phase 8 all/any/not retained (OQ-23/24) |
| D-110 | `bars_ago` / `ref` lookbacks; SEQUENCE within N bars (OQ-25) |
| D-111 | Named strategies as JSON files under `data/strategies/` |
