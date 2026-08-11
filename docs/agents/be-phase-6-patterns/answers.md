# Answers — BE Phase 6: Pattern Recognition (Agent B)

Decisive answers for [questions.md](./questions.md). Incorporated into [tech-design.md](./tech-design.md)
and [PHASE_6_HLD.md](../../../backend/docs/PHASE_6_HLD.md).

---

### Q1 → Answer

**Sparse True only on confirmation bar (`end_index`).** Pattern span lives in hit metadata
(`start_index` / `end_index`), not as a True run-length on the Series.

### Q2 → Answer

**Flat pattern name strings** matching `PatternName` values (e.g. `bullish_engulfing`,
`head_and_shoulders`, `rsi_regular_bearish`). No family prefix. Direction is encoded in
the name where relevant.

### Q3 → Answer

**No mutual exclusion.** Multiple Series may be True on the same bar independently.

### Q4 → Answer

**Yes.** `DOJI_BODY_MAX_RATIO = 0.1` of the full range. Gravestone: long upper wick,
negligible lower. Dragonfly: long lower wick, negligible upper. Standard doji: both wicks
present without extreme one-sided dominance.

### Q5 → Answer

**Body engulfing** — current `|open-close|` range fully covers prior body range; wicks
ignored for the engulf test. Direction from close vs open of the current candle.

### Q6 → Answer

**Wider classical default: `CLASSICAL_EQ_TOLERANCE_PCT = 0.015` (1.5%)** for double
top/bottom and H&S shoulder equality. Structure’s 0.15% EQ remains for swing labels only.

### Q7 → Answer

**Yes.** Impulse requires prior swing move ≥ `FLAG_IMPULSE_MIN_PCT = 0.03` (3%) before
the consolidation window. Consolidation length bounded by named min/max swing counts.

### Q8 → Answer

**Coarse % heuristics only** — rounded cup approximated by swing sequence (left rim, low,
right rim) with depth bounds; handle = shallow pullback after right rim. No curve fitting.

### Q9 → Answer

**Yes.** Confirmation = first bar that **closes** beyond neckline / boundary after the
pattern structure is recognized. That bar index is `end_index` and the Series True slot.
If no breakout within a look-ahead window, no hit (completed mode only).

### Q10 → Answer

**Sample oscillator at price swing indices** (confirmed swings from `structure`). Do not
run a second pivot algorithm on the oscillator for v1.

### Q11 → Answer

**MACD histogram (`MACD_HIST`)** for divergence comparisons.

### Q12 → Answer

**Yes — both regular and hidden** for RSI, MACD, Stoch, with distinct names
(e.g. `rsi_regular_bullish`, `rsi_hidden_bearish`, …).

### Q13 → Answer

**No REST in Phase 6.** Agent E skipped. Library only.

### Q14 → Answer

**No evaluator YAML hook.** Callers use `PatternResult.signals` Series directly until Phase 9.

### Q15 → Answer

**Yes — passthrough** `left_bars`, `right_bars`, `tolerance_pct` (structure EQ) into
`analyze_structure`, plus classical-specific tolerances as separate kwargs.

---

## Gate

Auto-approved — proceed to Agent D implementation (library-only; Agent E skipped).
