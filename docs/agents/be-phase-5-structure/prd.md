# PRD — BE Phase 5: Market Structure Detection

| Field | Value |
|---|---|
| **Status** | Approved (auto — no human-in-loop; product defaults below) |
| **Phase** | Backend Phase 5 |
| **Product intent** | [ROADMAP.md — Phase 5](../../../backend/docs/ROADMAP.md#phase-5--market-structure-detection) |
| **Prior contracts** | Decisions D-53–D-66; Phase 2 indicators as style reference; Phase 1 `get_candles()` data boundary |
| **Decisions** | D-53–D-66, D-59, D-61, D-63 (library-first), D-75 (phase renumber) |

---

## 1. Problem / Goal

### Problem

Classical patterns (Phase 6) and SMC (Phase 7) need a shared, auditable swing layer.
Today the platform has OHLCV + indicators but no swing highs/lows, HH/HL labeling,
trend-from-structure, or multi-timeframe structure context. Without this, every later
detector would reinvent pivots inconsistently.

### Goal

Ship a **`structure/` library** that, given an OHLCV candle series:

1. Detects swing highs / lows via symmetric pivot 5/5 (confirmed + provisional).
2. Labels swings `FIRST` / `HH` / `HL` / `LH` / `LL` / `EQH` / `EQL`.
3. Derives discrete S/R from the last `k` confirmed swings (recency-first).
4. Classifies trend (`uptrend` / `downtrend` / `range` / `undefined`) only on confirmed
   structural events, forward-filled on the candle index.
5. Exposes `StructureContext` for base + up to two HTF series with HTF trend forward-fill
   onto the base index (no HTF lookahead).

Success looks like: unit tests lock the contracts; `run_structure_report.py` can export
swings for manual BTC/USDT chart review; Phase 6+ can import `structure` without
touching `indicators/registry.py`.

---

## 2. User Roles

| Role | Description | Auth |
|---|---|---|
| **Library consumer (Phase 6/7, future DSL)** | Imports `structure` and calls pure/pipeline APIs on DataFrames. | N/A |
| **Developer / QA** | Runs pytest + optional report script against synced DB. | Local only |
| **Chart client** | Not a Phase 5 consumer unless a thin read-only API is explicitly added (default: **no**). | — |

---

## 3. Scope

### In scope (v1)

- New package `backend/structure/` (D-59) with types, swing detection, labeling, levels,
  trend classification, multi-TF context, and a single-TF analyze pipeline.
- Defaults: `left_bars=5`, `right_bars=5`, `tolerance_pct=0.0015`, `k=3` S/R.
- `confirmed_only=True` default for backtest-safe consumers (D-62).
- Unit tests under `backend/tests/structure/` covering pivots, labels, EQ tolerance,
  trend events, forward-fill, levels order, and StructureContext alignment.
- CLI `run_structure_report.py` for CSV/JSON export (D-60).
- `backend/docs/PHASE_5_HLD.md` + ROADMAP status update.

### Out of scope / deferred

| Item | Reason |
|---|---|
| ZigZag swings | D-54 |
| Vectorbt-style similarity / templates | D-61 → Phase 6 optional |
| `structure:` YAML evaluator hook | D-63 → Phase 6+ / OQ-23 |
| Merged S/R zones | D-57 discrete levels only |
| REST `/structure` endpoints | Library-first (D-63); thin read-only API only if design warrants — **default omit** |
| FE overlays for swings | Future FE phase |
| Pattern / SMC detectors | Phases 6–7 |

### Current codebase baseline (as of PRD)

- No `structure/` package.
- Session floor pivots (`PIVOT_*`) exist in indicators — **distinct** from swing structure.
- `get_candles()` is the sole data boundary for multi-TF loading.
- No `PHASE_5_HLD.md` yet (roadmap notes it must be written before implementation).

---

## 4. UX / API Flows

### 4.1 Single-TF analysis (library)

```
candles: DataFrame[ts, open, high, low, close, volume]
  → detect_swings(...)
  → label_swings(...)
  → structure_levels(..., k=3)
  → classify_trend(...)  # event-driven Series on candle index
  → StructureResult
```

### 4.2 Multi-TF context

```
StructureContext(symbol, base_tf, htf=[4h, 1d], start, end)
  → get_candles per TF
  → analyze each TF
  → forward-fill HTF trend onto base index (as-of join, no lookahead)
```

### 4.3 Report script

```
python run_structure_report.py --symbol BTC/USDT --timeframe 1h --start … --end …
  → writes swings (+ optional trend summary) under output/ for chart review
```

---

## 5. Acceptance Criteria

| ID | Criterion |
|---|---|
| **AC-1** | Symmetric pivot 5/5 detects swing high/low on `high`/`low` with strict inequalities; confirmation at `i + right_bars`. |
| **AC-2** | Labels follow D-65 (incl. EQH/EQL via D-55 tolerance); first of each kind is `FIRST`. |
| **AC-3** | `StructureLevels.support` / `.resistance` are length ≤ `k`, most-recent-first (D-64). |
| **AC-4** | `classify_trend` returns `pd.Series` of `Trend`; updates only on confirmed swings; forward-filled (D-66). |
| **AC-5** | Trend uses HH+HL → uptrend, LH+LL → downtrend; EQH/EQL or mixed → range; else undefined (D-56). |
| **AC-6** | `StructureContext` forward-fills HTF trend onto base without lookahead (D-58). |
| **AC-7** | Package is separate from `indicators/`; no evaluator YAML hook (D-59, D-63). |
| **AC-8** | `tests/structure/` pytest green; report script exists. |
| **AC-9** | `PHASE_5_HLD.md` + ROADMAP Phase 5 marked complete; agent A–H artifacts present. |

---

## 6. Non-goals / quality bar

- No TradingView parity requirement (D-60).
- Deterministic, backtest-safe confirmed path by default.
- Pure functions where possible; `StructureContext` may call `get_candles` (documented side effect: DB read).

---

## Gate

Auto-approved — Agent B may open clarifying questions; defaults above stand unless answers change them.
