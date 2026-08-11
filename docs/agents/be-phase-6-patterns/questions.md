# Clarifying Questions — BE Phase 6: Pattern Recognition

Review of [prd.md](./prd.md), ROADMAP Phase 6, OQ-13–15 defaults, and Phase 5 `structure/`.
Questions only — no proposed answers.

---

## Output contract

### Q1 — Series sparsity

**Question:** Confirm boolean Series are **sparse True only on `end_index` (confirmation bar)**, not True across the entire pattern span `[start, end]`?

### Q2 — Signal dict keying

**Question:** Should `PatternResult.signals` keys be the pattern name string (e.g. `bullish_engulfing`), or `name:direction`, or include family prefix (`candle.bullish_engulfing`)?

### Q3 — Multiple hits same bar

**Question:** If two patterns confirm on the same bar, both Series may be True independently — confirm no mutual exclusion?

---

## Candles (5a)

### Q4 — Doji body threshold

**Question:** Confirm doji uses `|close-open| / (high-low) <= 0.1` (or similar named constant), with gravestone/dragonfly distinguished by wick dominance?

### Q5 — Engulfing reference

**Question:** Confirm engulfing requires current body to fully cover prior body (open/close range), ignoring wicks — Nison body engulfing?

---

## Classical (5b)

### Q6 — Double top tolerance

**Question:** Confirm double top/bottom peak equality uses the same relative tolerance as structure EQ (0.15%) or a wider classical default (e.g. 1–2%)?

### Q7 — Flag / pennant impulse

**Question:** Confirm flag/pennant require a prior impulse leg measured as ≥ N% move over the swing before consolidation, with N as a named constant?

### Q8 — Cup & handle depth

**Question:** Confirm cup depth / handle depth use coarse % heuristics (not Bezier fitting) for v1?

### Q9 — Breakout confirmation

**Question:** For triangles/H&S/flags, is confirmation the bar that closes beyond the neckline / trendline, and is that bar the Series True index?

---

## Divergence (5c)

### Q10 — Oscillator pivots

**Question:** Compare oscillator values **at price swing bar indices** (sample indicator at price pivots), or run a separate pivot detect on the oscillator series?

### Q11 — MACD series

**Question:** Confirm MACD divergence uses **MACD histogram** (`MACD_HIST`), not the MACD line?

### Q12 — Regular vs hidden

**Question:** Confirm both regular and hidden are in scope for RSI, MACD, and Stoch, each emitting distinct pattern names?

---

## Scope / API

### Q13 — REST

**Question:** Confirm **no** `/api/v1/patterns` in this phase (Agent E = N/A)?

### Q14 — Evaluator hook

**Question:** Confirm no `pattern:` condition in `signals/evaluator.py` (Phase 9)?

### Q15 — Structure params passthrough

**Question:** Should `analyze_patterns` accept `left_bars` / `right_bars` / `tolerance_pct` and forward them to `analyze_structure`?
