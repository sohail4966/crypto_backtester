# PRD — BE Phase 6: Pattern Recognition

| Field | Value |
|---|---|
| **Status** | Approved (auto — no human-in-loop; product defaults below) |
| **Phase** | Backend Phase 6 |
| **Product intent** | [ROADMAP.md — Phase 6](../../../backend/docs/ROADMAP.md#phase-6--pattern-recognition) |
| **Prior contracts** | Phase 5 `structure/`; D-11 (boolean Series); D-53–D-66 swings; D-61 (no similarity search) |
| **Open questions resolved** | OQ-13, OQ-14, OQ-15 → product defaults (D-99–D-101) |

---

## 1. Problem / Goal

### Problem

Phase 5 ships swing structure, but the platform still cannot detect candlestick patterns,
classical chart patterns, or indicator divergences. Without a shared `patterns/` layer,
Phase 9 DSL and Phase 8 screener would reinvent inconsistent detectors.

### Goal

Ship a **`patterns/` library** that, given OHLCV (and Phase 5 swings / Phase 2 indicators):

1. **5a** Detects well-defined candlestick patterns (engulfing, hammer family, doji
   variants, morning/evening star, three soldiers/crows, harami).
2. **5b** Detects pragmatic rule-based classical patterns from confirmed swings
   (double top/bottom, H&S / inverse, triangles, flags, pennant, wedge, cup & handle).
3. **5c** Detects RSI / MACD / Stochastic regular and hidden divergence.
4. Outputs **boolean Series + metadata** compatible with the signal evaluator contract
   (same shape as indicator-based signals: True on confirmation bar; metadata carries
   start/end bars and key levels).

Success looks like: unit tests lock geometry on synthetic series; Phase 9 can later wire
`pattern:` YAML without changing detector math; no competing pivot definition (reuse
`structure`).

---

## 2. User Roles

| Role | Description | Auth |
|---|---|---|
| **Library consumer (Phase 8/9, future DSL)** | Imports `patterns` and calls detect / pipeline APIs. | N/A |
| **Developer / QA** | Runs `pytest tests/patterns/`. | Local only |
| **Chart / HTTP client** | Not a Phase 6 consumer by default (library-first; thin API omitted as low-risk deferral). | — |

---

## 3. Scope

### In scope (v1)

- Package `backend/patterns/` with types, candle detectors, classical detectors,
  divergence detectors, Series/metadata helpers, and `analyze_patterns` pipeline.
- Defaults documented per OQ-13–15 (see §5).
- Confirmed swings only for classical / divergence pivot legs (`confirmed_only=True`).
- Unit tests under `backend/tests/patterns/`.
- `backend/docs/PHASE_6_HLD.md` + ROADMAP Phase 6 status update.
- Decisions D-99–D-101 recorded; OQ-13–15 marked resolved.

### Out of scope / deferred

| Item | Reason |
|---|---|
| Vectorbt PRO similarity / template search | D-61 |
| `pattern:` YAML evaluator hook | Phase 9 / OQ-23 |
| REST `/patterns` chart overlays | Library-first; thin API not required for v1 |
| Formation / anticipatory mode | OQ-15 → completed-only in v1 |
| SMC (BOS, FVG, OB) | Phase 7 |
| FE pattern overlays | Future FE |

### Current codebase baseline (as of PRD)

- `structure/` complete (Phase 5).
- Indicators: RSI, MACD_HIST, STOCH_K available via `indicators/`.
- Signals evaluator: boolean Series from indicator conditions; no pattern registry yet.
- No `patterns/` package; no `PHASE_6_HLD.md`.

---

## 4. UX / API Flows

### 4.1 Full analysis (library)

```
candles: DataFrame[ts, open, high, low, close, volume]
  → detect_candles(...)
  → detect_classical(..., swings from analyze_structure(confirmed_only=True))
  → detect_divergence(..., indicator series)
  → PatternResult { hits, signals: dict[name → bool Series] }
```

### 4.2 Single-family helpers

Callers may import `detect_candlestick_patterns`, `detect_classical_patterns`,
`detect_divergences` independently. Pipeline wraps all three.

### 4.3 Signal-evaluator compatibility

```python
result.signals["bullish_engulfing"]  # pd.Series[bool], index = candle ts
# True only on confirmation bar (pattern end_index)
hit.metadata / hit fields: start_index, end_index, levels, confidence
```

No YAML hook in Phase 6 — consumers combine Series with `&` / `|` in Python or wait for DSL.

---

## 5. Product defaults (auto-resolved open questions)

### OQ-13 — Definition source of truth → **D-99**

| Category | Primary reference (v1) |
|---|---|
| Candlesticks (5a) | Steve Nison / industry-standard body–wick geometry (TA-Lib CDL*-compatible ratios) |
| Classical (5b) | Thomas Bulkowski, *Encyclopedia of Chart Patterns* — simplified measurable rules |
| Divergence (5c) | John Murphy / standard TA: price pivot vs oscillator pivot disagreement |

Each detector docstring cites the category reference. Rules are approximations; thresholds
are named constants for later tuning.

### OQ-14 — Confidence → **D-100**

- **Primary:** binary boolean Series (evaluator-ready).
- **Secondary:** each `PatternHit.confidence ∈ [0, 1]` in metadata (quality heuristic).
- Default: no confidence gate — any detection sets Series True. Callers may filter hits.

### OQ-15 — Timing → **D-101**

- **v1 default:** `mode="completed"` only — emit on the confirmation / breakout bar.
- Mid-formation anticipatory signals **deferred** (screener / later phase).
- Backtest path never emits forming patterns (avoids look-ahead).

---

## 6. Acceptance Criteria

| ID | Criterion |
|---|---|
| **AC-1** | All ROADMAP 5a candle patterns detect on synthetic fixtures with documented geometry |
| **AC-2** | All ROADMAP 5b classical patterns detect via confirmed swings with pragmatic rules |
| **AC-3** | RSI / MACD / Stoch regular + hidden divergence detect on synthetic pivot setups |
| **AC-4** | Output = boolean Series aligned to candle index + hits with start/end/levels/confidence |
| **AC-5** | Classical/divergence use `structure` confirmed swings; no duplicate pivot algorithm |
| **AC-6** | Package separate from `indicators/`; no evaluator YAML hook |
| **AC-7** | `pytest tests/patterns/` green |
| **AC-8** | `PHASE_6_HLD.md` + ROADMAP Phase 6 Complete + A–H artifacts |
| **AC-9** | OQ-13–15 resolved in OPEN_QUESTIONS; D-99–D-101 in DECISIONS |

---

## 7. Non-goals / risks

- Classical patterns will have false positives — tunable thresholds, not “perfect” geometry.
- Cup & handle is the most subjective; v1 uses a coarse rounded-bottom + handle heuristic.
- No claim of TradingView / Bulkowski statistical parity.

---

## 8. Gate

Auto-approved. Proceed to Agent B questions (narrow) → Agent C tech design → Agent D impl.
Agent E (REST/FE) default **skipped** unless design finds a low-risk thin read-only need
(expected: skip).
