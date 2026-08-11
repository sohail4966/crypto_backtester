# Clarifying Questions — BE Phase 9: Full Trading DSL

Review of [prd.md](./prd.md), ROADMAP Phase 9, OQ-23–25 drafts, and `signals/evaluator.py`.
Questions only — no proposed answers.

---

## Grammar

### Q1 — Nested tree shape

**Question:** Confirm Option A: groups are `{"op": "AND"|"OR"|"NOT", "conditions": [...]}`
(NOT takes a single-element list), not Option B flat logic tokens?

### Q2 — Legacy `all`

**Question:** Keep `{"all": [...]}` as a permanent AND alias, or migrate-only with deprecation?

### Q3 — Leaf discrimination

**Question:** Confirm leaf kinds are discriminated by keys: `indicator` | `field` | `smc` |
`pattern` | group (`op`/`all`) | `SEQUENCE`?

---

## Multi-timeframe

### Q4 — Frame supply

**Question:** Does `evaluate_signals` accept an optional `frames: dict[str, DataFrame]`
for HTF candles, or must the evaluator always resample from base OHLCV?

### Q5 — Alignment rule

**Question:** Confirm look-ahead-safe rule: at base bar open `t`, use HTF values only from
bars whose **close time ≤ t** (completed HTF only)?

### Q6 — Same-TF omit

**Question:** If `timeframe` is omitted or equals the base TF, evaluate on the base frame
with no alignment step?

---

## Lookback / compare

### Q7 — `ref` shape

**Question:** Confirm RHS lookback uses `ref: {field|indicator, ..., bars_ago: N}` as in
OQ-25 draft, and LHS may also carry `bars_ago`?

### Q8 — Cross-indicator

**Question:** Confirm existing `compare: "close" | {indicator, params}` remains the
cross-series path (no new syntax required)?

---

## Sequence

### Q9 — SEQUENCE semantics

**Question:** Confirm pragmatic v1: ordered legs; True on bar `i` when the last leg is
True at `i` and each prior leg was True at least once in the preceding `within_bars`
window (non-overlapping order preserved)?

### Q10 — SEQUENCE length

**Question:** Allow 2+ legs, or only exactly two for v1?

---

## Schema / library / API

### Q11 — Version field

**Question:** Confirm `schema_version: "1"` (string) required on new strategies, optional
on legacy dicts (default `"1"` when missing)?

### Q12 — Strategy library

**Question:** File-based JSON store under `data/strategies/` — confirm no DB migration
in Phase 9?

### Q13 — REST

**Question:** Confirm Agent E skipped (no `/dsl` HTTP in v1)?

### Q14 — Pattern / SMC

**Question:** Confirm `pattern: <name>` and existing `smc:` remain first-class leaves
composable inside AND/OR/NOT/SEQUENCE?

### Q15 — Screener coexistence

**Question:** Confirm Phase 9 must not modify screener packages; document import points
only (`dsl.validate_strategy`, `evaluate_signals`)?
