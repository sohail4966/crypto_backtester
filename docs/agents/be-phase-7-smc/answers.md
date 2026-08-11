# Answers — BE Phase 7: Smart Money Concepts (SMC) (Agent B)

Decisive answers for [questions.md](./questions.md). Incorporated into
[tech-design.md](./tech-design.md) and [PHASE_7_HLD.md](../../../backend/docs/PHASE_7_HLD.md).

---

### Q1 → Answer

**ICT-leaning** as the documented default per concept (D-96). Not Mentfx/TTC-primary.
Users may retune parameters; docs state this is one interpretation.

### Q2 → Answer

Default **`full_fill`**: gap invalidated when price trades through the far edge
(high ≥ gap_top for bearish FVG, or low ≤ gap_bottom for bullish FVG). Overrides:
`touch`, `midpoint`, `full_fill` (D-97 / OQ-20).

### Q3 → Answer

**Yes — Phase 5 only.** Import `structure` swings/trend; no second pivot engine.

### Q4 → Answer

**Yes.** BOS = close break of the relevant confirmed swing **with** current structure
trend; CHOCH = close break **against** trend. Wick-only breaks do not count for
BOS/CHOCH (sweeps own wick logic).

### Q5 → Answer

**Yes.** A swing is usable only when `confirmation_index is not None` and
`confirmation_index <= i` at evaluation bar `i`.

### Q6 → Answer

**Last opposing body candle before the BOS impulse bar.** Zone = candle **body**
`[min(open, close), max(open, close)]` by default; `ob_use_wick_range=True` opts into
`[low, high]`.

### Q7 → Answer

**Same-bar wick beyond + close back inside.** No mandatory next-bar confirmation in v1.

### Q8 → Answer

**Breaker** = OB failed via close through the invalidating side → role flip event on
that bar (and optional retest signals later can be v2). **Mitigation** = first return
of price into a still-valid OB zone (touch of zone).

### Q9 → Answer

Named conditions are **event-bar True** (detection / break / sweep / mitigate bar).
Zone “active” state is available on event metadata / pipeline result, not as a level
hold in the default boolean Series.

### Q10 → Answer

**Additive `"smc"` key** in `SignalCondition` + evaluator branch. Do **not** register
into `indicators/registry.py` (avoids Phase 6 collision; Open/Closed via dispatch).

### Q11 → Answer

**No REST / no FE** in Phase 7.

### Q12 → Answer

**Yes.** Own `smc/` + `tests/smc/` + docs; evaluator/types get only the `"smc"` branch.

### Q13 → Answer

**No dedicated report CLI required.** Tests + HLD + optional `analyze_smc` for
notebooks/scripts are enough. (Phase 5 D-60 was structure-specific.)

---

## Gate

Auto-approved — proceed to Agent C tech design / Agent D implementation.
