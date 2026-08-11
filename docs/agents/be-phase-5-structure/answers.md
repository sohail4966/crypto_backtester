# Answers — BE Phase 5: Market Structure Detection (Agent B)

Decisive answers for [questions.md](./questions.md). Incorporated into [tech-design.md](./tech-design.md) and [PHASE_5_HLD.md](../../../backend/docs/PHASE_5_HLD.md).

---

### Q1 → Answer

**Left-only + available-right provisional candidates in the trailing window.** Any bar `i` with `i > n - 1 - right_bars` that is strictly greater (high) / less (low) than its full left window and all **available** right bars so far is marked `provisional=True`. Confirmed pivots require the full right window. Callers using `confirmed_only=True` drop provisionals.

### Q2 → Answer

**Use labels of the most recent confirmed high and most recent confirmed low.** Those labels already encode comparison to the prior same-kind swing (D-65). Do not recompute raw prices for trend except via those labels.

### Q3 → Answer

**`EQH` or `EQL` on the latest high or latest low → `range`.** Mixed directional pairs (e.g. HH + LL) also → `range`. Only HH+HL → uptrend; LH+LL → downtrend.

### Q4 → Answer

Align to **`ts` as UTC DatetimeIndex** (set inside the pipeline if needed). If fewer than `left_bars + right_bars + 1` bars, return a Series of `Trend.UNDEFINED` aligned to all rows (or empty Series if input empty).

### Q5 → Answer

**Confirmed only** for `structure_levels`. Provisional never enter S/R lists.

### Q6 → Answer

**Both:** `StructureContext.from_frames(base, htfs: Mapping[str, DataFrame])` for pure tests, and `StructureContext.load(...)` that calls `get_candles` for the report script / future API.

### Q7 → Answer

**As-of on `ts`:** for each base timestamp, take the last HTF trend observation with `htf_ts <= base_ts`. Trend values on the HTF series already respect confirmation lag within that TF; do not peek at future base bars.

### Q8 → Answer

**Fail hard with `ValueError`** naming the empty TF when `load()` is used and a requested series is empty. `from_frames` may accept empty only if caller opts in; default same hard fail for consistency.

### Q9 → Answer

**No REST in Phase 5.** Agent E is N/A / deferred. Library + report script only (D-63). Chart clients wait for a later phase if an overlay API is needed.

### Q10 → Answer

**CSV (+ optional JSON) under `output/`.** No PNG required. Manual chart review is human + TradingView/our chart; export is enough (D-60).

### Q11 → Answer

**Yes — narrow public surface** as listed. Internal modules may keep helpers private (leading underscore or omit from `__all__`).

### Q12 → Answer

**Yes — plateaus are not pivots.** Strict inequalities only (D-53 / OQ-50).

### Q13 → Answer

**No forced alternation.** Pivot detection is independent per side; consecutive same-kind swings are allowed. Labeling and trend still compare within kind only.

---

## Gate

Auto-approved — proceed to Agent D implementation (library-only; Agent E skipped).
