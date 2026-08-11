# Phase 6 High Level Design — Pattern Recognition

**Status:** Complete — see [Phase 6 Completion Assessment](#phase-6-completion-assessment)  
**Prerequisite:** Phase 5 `structure/`; Phase 2 indicators (RSI / MACD / Stoch)  
**Decisions:** D-99, D-100, D-101; D-11, D-61, D-62  
**Agent artifacts:** [docs/agents/be-phase-6-patterns/](../../docs/agents/be-phase-6-patterns/)  
**Next phase after this:** [Phase 7 — SMC](ROADMAP.md#phase-7--smart-money-concepts-smc) (parallel track) / Phase 8 screener / Phase 9 DSL

---

## Starting Point

Phase 5 provides confirmed swings. Indicators provide oscillators. The platform still
lacked candlestick, classical, and divergence detectors that emit evaluator-compatible
boolean Series.

**Phase 6 goal:** Ship `patterns/` — rule-based 5a/5b/5c detectors with sparse boolean
Series + hit metadata (start/end/levels/confidence).

---

## Done Criteria

1. Candlestick patterns from ROADMAP 5a detect on synthetic fixtures.
2. Classical patterns from ROADMAP 5b use confirmed `structure` swings + close breakout.
3. RSI / MACD histogram / Stoch regular + hidden divergences detect.
4. Output = boolean Series (True on confirmation bar) + `PatternHit` metadata (D-100, D-101).
5. OQ-13–15 resolved (D-99–D-101).
6. No evaluator YAML hook; not in `indicators/` registry; no REST (library-first).
7. `pytest tests/patterns/` green; ROADMAP Phase 6 marked complete.

---

## Architecture

```
patterns/
  types.py         PatternName, PatternFamily, PatternHit, PatternResult
  candles.py       5a OHLC geometry
  classical.py     5b swing geometry + breakout
  divergence.py    5c oscillator @ price pivots
  series.py        hits → sparse bool Series
  pipeline.py      analyze_patterns
```

```
OHLCV → candles
     → analyze_structure(confirmed_only=True) → classical + divergence
     → PatternResult { hits, signals }
```

---

## Key contracts

| Contract | Rule |
|---|---|
| Series True | Only at `end_index` (confirmation / breakout bar) |
| Confidence | Metadata 0–1; does not gate emission |
| Classical EQ | 1.5% peak equality (wider than structure 0.15%) |
| Breakout | Close beyond neckline/bound within 20 bars |
| Divergence sample | Oscillator at price swing indices |
| MACD series | `MACD_HIST` |
| Mode | `completed` only |

---

## Out of scope

| Item | Phase |
|---|---|
| Similarity / template search | Deferred (D-61) |
| `pattern:` YAML evaluator | 9 |
| Formation mode | Later / screener |
| REST overlays | Later |
| SMC | 7 |

---

## Phase 6 Completion Assessment

Phase 6 delivers a **library-only** `patterns/` package covering candlesticks, classical
chart patterns, and RSI/MACD/Stoch divergences, with evaluator-compatible boolean Series.

### Evidence checked

| Check | Result | Notes |
|---|---|---|
| `patterns/` package | Done | types, candles, classical, divergence, series, pipeline |
| Unit suite | Passing | `pytest tests/patterns/` → **30 passed** |
| Structure reuse | Done | classical/divergence use confirmed swings |
| No evaluator hook | Done | `signals/evaluator.py` untouched |
| No REST | Done | Agent E skipped |
| OQ-13–15 | Resolved | D-99, D-100, D-101 |
| HLD + agent A–H | Done | `docs/agents/be-phase-6-patterns/` |

### Rating breakdown

| Area | Score | Comment |
|---|---|---|
| Architecture alignment | 9/10 | Matches D-11 / D-99–101; clean separation |
| Algorithm correctness | 8/10 | Synthetic fixtures lock rules; live false-positive tuning expected |
| Test coverage | 8.5/10 | Per-pattern unit tests + pipeline Series packing |
| Documentation | 9/10 | PHASE_6_HLD, ROADMAP, PRD/tech-design/answers |
| Scope discipline | 9.5/10 | Library-only; no similarity, REST, or YAML hook |

### Known gaps (acceptable for Phase 6)

- Classical detectors are pragmatic approximations — expect threshold tuning on live data.
- Cup & handle uses coarse swing heuristics (no curve fit).
- Inverted hammer and shooting star share upper-wick geometry (context not fully modeled).
- No live BTC/USDT false-positive audit in this pipeline.

### Completion verdict

Phase 6 is **complete**. Consumers import `from patterns import analyze_patterns` (or
narrower detectors) and combine `PatternResult.signals` Series until Phase 9 adds YAML.
