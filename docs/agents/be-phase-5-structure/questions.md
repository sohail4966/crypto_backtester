# Clarifying Questions — BE Phase 5: Market Structure Detection

Review of [prd.md](./prd.md), ROADMAP Phase 5, and D-53–D-66. Questions only — no proposed answers.

---

## Algorithm / contracts

### Q1 — Provisional swing definition

D-62 requires confirmed + provisional. Confirmed = pivot with full `right_bars` future bars.

**Question:** Is a provisional swing any bar in the trailing `right_bars` window that is a left-only extreme (strictly greater/less than left neighbors and all available right neighbors so far), or only the single latest candidate tip?

### Q2 — Trend “latest pair” semantics

D-56 says uptrend = HH + HL from last two highs and two lows.

**Question:** Confirm trend uses the **labels of the most recent confirmed high and most recent confirmed low** (each already compared to its prior of the same kind), not a recompute that ignores EQ labels?

### Q3 — Insufficient swings after EQ

**Question:** If the latest high is `EQH` (or low `EQL`), confirm trend is **`range`** even when the other side is a clear HH/HL — not `undefined`?

### Q4 — Candle index for trend Series

**Question:** Should `classify_trend` align to the DataFrame’s `ts` column as a DatetimeIndex, or to whatever index the caller already set? Confirm empty / short series → all `undefined` (or empty Series)?

### Q5 — Levels and provisional

**Question:** Confirm S/R (`structure_levels`) uses **confirmed swings only**, never provisional?

---

## Multi-TF / IO

### Q6 — StructureContext constructor vs factory

**Question:** Prefer `StructureContext.from_loader(symbol, base_tf, htfs, start, end)` calling `get_candles`, plus a pure `StructureContext.from_frames(...)` for tests — or only the loader path?

### Q7 — HTF forward-fill timestamp

**Question:** Confirm HTF trend is as-of joined on candle open time (`ts`): base bar gets the last HTF trend whose HTF bar `ts <= base_ts` (no lookahead into an unclosed HTF bar’s future confirmation beyond what that HTF series already encoded)?

### Q8 — Missing HTF data

**Question:** If an HTF `get_candles` returns empty, fail hard (`ValueError` / `DataGapError`) or continue with that HTF trend all-`undefined`?

---

## Scope / API / FE

### Q9 — REST surface

PRD defaults to no REST (D-63).

**Question:** Confirm **no** `/api/v1/structure` in this phase (Agent E = N/A)?

### Q10 — Report script output format

**Question:** CSV of swings (+ JSON sidecar optional) under `output/structure_*.csv` enough for D-60, or also require a PNG overlay?

### Q11 — Package public exports

**Question:** Confirm `__init__.py` re-exports the primary types + `detect_swings`, `label_swings`, `structure_levels`, `classify_trend`, `analyze_structure`, `StructureContext` only (no private helpers)?

---

## Edge cases

### Q12 — Equal neighbor bars (non-strict)

Strict `>` / `<` means plateaus are not pivots.

**Question:** Confirm plateau highs (equal neighbors) produce **no** swing at those bars — intentional per D-53?

### Q13 — Alternation requirement

**Question:** Must swing highs and lows alternate, or can the detector emit consecutive highs (e.g. after a higher high without an intervening low pivot)?
