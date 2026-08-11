# Clarifying Questions — BE Phase 7: Smart Money Concepts (SMC)

Review of [prd.md](./prd.md), ROADMAP Phase 7, OQ-19–20, Phase 5 `structure/`.
Questions only — no proposed answers.

---

## Reference / invalidation

### Q1 — SMC reference framework (OQ-19)

**Question:** Confirm primary reference is **ICT-leaning** (document per-concept rules),
not Mentfx / The Trading Channel as the binding default?

### Q2 — FVG invalidation default (OQ-20)

**Question:** Default fill/invalidation rule: `touch` (near edge), `midpoint` (50%),
or `full_fill` (through far edge)? Confirm others remain configurable overrides?

---

## Structure coupling

### Q3 — Pivot source

**Question:** Confirm detectors must use Phase 5 `detect_swings` / `analyze_structure`
(confirmed swings) and must **not** reimplement pivot math?

### Q4 — BOS vs CHOCH vs structure trend

**Question:** Confirm BOS = break **with** `classify_trend` bias, CHOCH = first break
**against** bias, using **close** (not wick-only) for the break?

### Q5 — Confirmation lag

**Question:** May a swing only be used for BOS/CHOCH/sweep once
`confirmation_index <= current_bar` (no lookahead)?

---

## Concept semantics

### Q6 — Order Block anchoring

**Question:** Bullish OB = last bearish (close < open) candle before the impulse bar
that prints bullish BOS (mirror for bearish)? Zone = that candle’s `[min(o,c), max(o,c)]`
body, or full `[low, high]` wick range?

### Q7 — Liquidity sweep

**Question:** Confirm sweep = wick beyond confirmed swing + **close back inside** on
the same bar (no mandatory next-bar confirmation)?

### Q8 — Breaker vs mitigation

**Question:** Breaker = OB invalidated by **close through** opposite side (role flip);
Mitigation = price **returns into** OB zone without requiring full invalidation first?

### Q9 — Signal Series semantics

**Question:** Named conditions True only on the **event bar** (detection bar), not
while a zone remains “fresh”?

---

## Integration / scope

### Q10 — Evaluator shape

**Question:** Prefer `{"smc": "bos", "side": "bullish", "params": {...}}` additive key
(vs registering `SMC_BOS` in `indicators/registry.py`)?

### Q11 — REST / FE

**Question:** Confirm **no** `/smc` REST and no FE work in Phase 7?

### Q12 — Parallel Phase 6

**Question:** Confirm Phase 7 must not create `patterns/` or edit Phase 6 files; only
`smc/`, tests, docs, and a minimal `"smc"` evaluator branch?

### Q13 — Report CLI

**Question:** Is a `run_smc_report.py` required, or tests + HLD sufficient (unlike
Phase 5’s D-60 chart export)?
