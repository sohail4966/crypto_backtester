# Open Questions

This document tracks every unresolved question across the project. Each question
must be answered before the phase that depends on it begins. When a decision is made,
move it to DECISIONS.md with its full reasoning and mark it resolved here.

Questions are grouped by phase/area and tagged with a priority:
- **[BEFORE POC]** — must resolve before writing any code
- **[BEFORE PHASE N]** — must resolve before that phase begins
- **[ANYTIME]** — can be answered progressively; no hard blocker

---

## Data Layer

### OQ-01 — Which timeframes to store
**Priority:** BEFORE PHASE 1  
**Status:** **Resolved → D-17**  
**Question:** Store only 1d for the POC, but what is the full set of timeframes
to support? Options: 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w.  
**Why it matters:** Storing finer granularity (1h or below) enables more strategy types
and future rollups, but multiplies storage size and fetch time significantly.  
**Things to consider:**
- Most swing/pattern traders use 1h, 4h, 1d as primary timeframes
- Scalping requires 1m/5m but is a different user profile
- TimescaleDB continuous aggregates can roll 1h → 4h → 1d automatically later
**Current assumption for POC:** 1d only.  
**Decision:** Store only canonical `1m` candles in the database. Derive higher
timeframes from `1m` data through `get_candles()` / repository aggregation.

---

### OQ-02 — How far back to fetch history
**Priority:** BEFORE PHASE 1  
**Status:** **Resolved → D-18**  
**Question:** For each symbol and timeframe, how far back should the initial historical
fetch go?  
**Why it matters:** More history = more backtest signal and better pattern validation.
Less history = faster initial setup and smaller DB.  
**Options:**
- 2 years (fast, enough for basic backtesting)
- 5 years (covers multiple market cycles for crypto)
- Max available (varies by exchange; Binance has BTC/USDT from 2017)  
**Things to consider:** Crypto has distinct market cycles roughly every 3–4 years.
Testing a strategy across only one cycle is not robust.  
**Current assumption for POC:** 2 years.  
**Decision:** Backfill depth is configured per symbol in `data.yaml` as
`symbol -> history`.

---

### OQ-03 — Primary exchange source
**Priority:** BEFORE PHASE 1  
**Status:** **Resolved → D-19**  
**Question:** Which exchange is the canonical data source? Binance is the obvious
default for crypto (highest liquidity, longest history, reliable API), but should
there be a fallback?  
**Why it matters:** Exchange data quality differs. If Binance has a gap or rate limit,
what happens?  
**Options:**
- Binance as sole source (simplest)
- Binance primary + Bybit/OKX as fallback
- Pluggable exchange config per symbol  
**Decision:** Use spot data only. Binance is primary; fallback order is Bybit, then OKX.

---

### OQ-04 — Incremental update strategy
**Priority:** BEFORE PHASE 1  
**Status:** **Resolved → D-20**  
**Question:** After the initial historical fetch, how do new candles get added?  
**Why it matters:** Re-fetching everything on each run wastes time and API calls.
Need a "fetch from last stored timestamp" approach.  
**Things to consider:**
- Must handle the case where the last stored candle is the current in-progress (unclosed) candle
- Exchange APIs return the current unclosed candle — should it be stored or skipped?
- What if a candle is updated retroactively by the exchange (rare but happens)?  
**Decision:** Fetch from `MAX(ts) - 1 minute`, skip in-progress candles, and never
overwrite already stored closed candles.

---

### OQ-05 — Handling data gaps
**Priority:** BEFORE PHASE 1  
**Status:** **Resolved → D-21**  
**Question:** What happens if a candle is missing (exchange downtime, API error)?  
**Options:**
- Forward-fill (repeat last candle) — common but distorts volume
- Leave the gap and let downstream code handle it
- Flag the gap in the DB and skip that candle in calculations  
**Why it matters:** Indicators like RSI break or produce wrong values on gaps.
Backtest engine can misfire on missing bars.  
**Decision:** Persist gaps in a `data_gaps` table and auto re-fetch those ranges on
the next sync. Per-symbol sync failures are logged and skipped; the rest of the sync
continues.

---

### OQ-06 — TimescaleDB → ClickHouse migration trigger
**Priority:** BEFORE PHASE 7  
**Question:** What is the specific condition that triggers the migration from
TimescaleDB to ClickHouse?  
**Options:**
- Migrate when scan across 50+ symbols takes more than X seconds
- Migrate at the start of Phase 7 regardless
- Benchmark at the start of Phase 7 and decide then  
**Why it matters:** Migration is cheap because of the `get_candles()` boundary, but
still takes time. Better to decide the trigger criteria in advance.  
**Decision needed:** Before Phase 7 begins.

---

## Indicator Layer

Phase 2 indicator questions **OQ-08 through OQ-38** are resolved (see D-27 through D-36).
Remaining open items below are for later phases.

### OQ-07 — RSI implementation variant
**Priority:** BEFORE POC  
**Status:** **Resolved → D-13**  
**Question:** Which RSI smoothing method to use: Wilder's smoothing (RMA) or
standard EMA?  
**Why it matters:** TradingView uses Wilder's smoothing. If the implementation uses
a different method, RSI values will not match TradingView, which is the primary
sanity-check reference.  
**Decision:** Use Wilder's smoothing (RMA) to match TradingView exactly. Verify by
spot-checking computed values against TradingView for 3–5 BTC/USDT 1d dates before
trusting any backtest output. See D-13 for full reasoning.

---

### OQ-08 — VWAP variant to implement
**Priority:** BEFORE PHASE 2  
**Status:** **Resolved → D-29**  
**Question:** VWAP has multiple variants: session VWAP (resets daily), rolling VWAP
(N-bar window), anchored VWAP (from a specific date/event). Which to implement first?  
**Decision:** Implement **both** rolling (default) and UTC session variants via
`params.variant` on the `VWAP` registry function.

---

### OQ-09 — Indicator parameter validation
**Priority:** BEFORE PHASE 2  
**Status:** **Resolved → D-30**  
**Question:** Should indicator functions validate their parameters (e.g. period must
be > 0, period < len(series)) or fail silently with NaN output?  
**Decision:** Raise `ValueError` for invalid parameters; evaluator maps to
`InvalidSignalError`. Warmup NaNs for valid params are normal and not errors.

---

### OQ-32 — Indicator function signature convention
**Priority:** PHASE 2  
**Status:** **Resolved → D-31**  
**Decision:** Separate Series arguments (`close`, optional `high`, `low`, `volume`).

---

### OQ-33 — Multi-output indicator registry design
**Priority:** PHASE 2  
**Status:** **Resolved → D-32**  
**Decision:** Separate registry keys per output series (`MACD_HIST`, not `MACD` with
a default line).

---

### OQ-34 — Phase 2 implementation scope
**Priority:** PHASE 2  
**Status:** **Resolved → D-33**  
**Decision:** Tier 1 + all Tier 2 TA-Lib indicators + as many Tier 2 custom indicators
as feasible in one pass.

---

### OQ-35 — Tier 3 deferrals
**Priority:** PHASE 2  
**Status:** **Resolved → D-34**  
**Decision:** Defer VPVR, Fibonacci tools, ZigZag, Puell Multiple, Guppy MACD, KDJ,
Elder-RSI, Copenhagen Index.

---

### OQ-36 — Pivot point session boundaries
**Priority:** PHASE 2  
**Status:** **Resolved → D-35**  
**Decision:** Prior UTC calendar day on intraday timeframes; prior bar on `1d`.

---

### OQ-37 — SMA implementation source
**Priority:** PHASE 2  
**Status:** **Resolved → D-28, D-27**  
**Decision:** TA-Lib only; remove POC pandas SMA.

---

### OQ-38 — Ichimoku default parameters
**Priority:** PHASE 2  
**Status:** **Resolved → D-36**  
**Decision:** 9, 26, 52, displacement 26.

---

## Market Structure

### OQ-10 — Swing detection algorithm
**Priority:** BEFORE PHASE 4  
**Status:** **Resolved → D-53, D-54**  
**Decision:** Symmetric pivot **`left_bars=5`**, **`right_bars=5`**, strict `>` / `<` on
`high`/`low`. ZigZag deferred.

---

### OQ-11 — Equal highs / equal lows handling
**Priority:** BEFORE PHASE 4  
**Status:** **Resolved → D-55**  
**Decision:** **`tolerance_pct: 0.0015`** (0.15%) default, configurable.

---

### OQ-12 — Multi-timeframe structure hierarchy
**Priority:** BEFORE PHASE 4  
**Status:** **Resolved → D-58, D-63**  
**Decision:** `StructureContext` + forward-fill HTF onto base TF (default base `1h`, HTF
`4h` + `1d`). **Library only** in Phase 4 — no evaluator YAML hook yet.

---

### OQ-51 — Vectorbt-style pattern similarity in Phase 4
**Priority:** PHASE 4  
**Status:** **Resolved → D-61**  
**Question:** Should Phase 4 include vectorbt PRO–style template matching (`find_pattern`,
similarity scores, projections)?  
**Decision:** **No.** Phase 4 is pivot/fractal swing structure only. Similarity search
is deferred to **Phase 5** if added.

---

### OQ-45 — Confirmed vs provisional swings
**Priority:** PHASE 4  
**Status:** **Resolved → D-62**  
**Decision:** API returns both; backtest/signals use **`confirmed_only=True`** default.

---

### OQ-46 — Swing price field
**Priority:** PHASE 4  
**Status:** **Resolved → D-53**  
**Decision:** **`high`** for swing highs, **`low`** for swing lows.

---

### OQ-47 — S/R zones vs discrete levels
**Priority:** PHASE 4  
**Status:** **Resolved → D-57**  
**Decision:** **Discrete levels**, **`k=3`** swings.

---

### OQ-48 — Default pivot width
**Priority:** PHASE 4  
**Status:** **Resolved → D-53**  
**Decision:** **`left_bars=right_bars=5`** global default.

---

### OQ-49 — Evaluator integration in Phase 4
**Priority:** PHASE 4  
**Status:** **Resolved → D-63**  
**Decision:** **Library only**; no `structure:` YAML hook in Phase 4.

---

### OQ-50 — Strict pivot comparison
**Priority:** PHASE 5 (market structure)  
**Status:** **Resolved → D-53**  
**Decision:** Strict **`>`** / **`<`** vs neighbors.

---

## Phase 4 — Client API

### OQ-52 — Authentication
**Priority:** PHASE 4  
**Status:** **Resolved → D-69**  
**Decision:** **No auth** — all endpoints public.

---

### OQ-53 — Replay session persistence
**Priority:** PHASE 4  
**Status:** **Resolved → D-71, D-78**  
**Decision:** **In-memory** in Phase 4; DB table → **Phase 11**.

---

### OQ-54 — Default watchlist on user create
**Priority:** PHASE 4  
**Status:** **Resolved**  
**Decision:** Auto-create **"Default"** watchlist with all active symbols (recommended).

---

### OQ-55 — Candle limit default
**Priority:** PHASE 4  
**Status:** **Resolved → D-79**  
**Decision:** Default **1000**, max **5000**.

---

### OQ-56 — Replay step vs display timeframe
**Priority:** PHASE 4  
**Status:** **Resolved**  
**Decision:** **`step_timeframe`** may differ from display **`timeframe`**.

---

### OQ-57 — Indicator batch compute
**Priority:** PHASE 4  
**Status:** **Resolved**  
**Decision:** Single **`POST /indicators/compute`** batch endpoint.

---

### OQ-58 — Live candle streaming in Phase 4
**Priority:** PHASE 4  
**Status:** **Resolved → D-78**  
**Decision:** **No live chart tail** in Phase 4. Historical REST + replay WS only.
Live streaming → **Phase 11**.

---

## Pattern Recognition

### OQ-13 — Pattern definition source of truth
**Priority:** BEFORE PHASE 5  
**Question:** Which reference defines each classical chart pattern? Options include
Bulkowski's "Encyclopedia of Chart Patterns," Thomas Bulkowski's website, John Murphy's
"Technical Analysis of the Financial Markets," or a custom definition.  
**Why it matters:** Without a single reference, every pattern becomes a moving target.
Users will argue about whether a detected pattern is "correct." Documenting the
reference per pattern makes the implementation auditable.  
**Decision needed:** Choose a primary reference per pattern category before Phase 5 starts.

---

### OQ-14 — Pattern confidence scoring
**Priority:** BEFORE PHASE 5  
**Question:** Should pattern detection return a binary result (pattern found / not found)
or a confidence score (0–1)?  
**Why it matters:** Real patterns rarely meet strict geometric criteria perfectly.
A confidence score allows users to filter by quality. A binary result is simpler to
implement and use in conditions.  
**Options:**
- Binary: simpler, easier to use in signal conditions
- Score: more realistic, enables "only show high-quality patterns," harder to implement  
**Decision needed:** Before Phase 5 pattern API is designed.

---

### OQ-15 — Pattern detection timing: completion vs formation
**Priority:** BEFORE PHASE 5  
**Question:** Should a pattern be emitted when it is fully formed (confirmation bar) or
during formation (anticipatory)?  
**Why it matters:** In a backtest, emitting mid-formation introduces look-ahead bias.
In a screener, traders often want to know a pattern is forming before it completes.  
**Decision needed:** Probably two modes, but the exact API needs to be defined before Phase 5.

---

## Backtesting

### OQ-16 — Multiple position management rules
**Priority:** BEFORE PHASE 3  
**Status:** **Resolved → D-43**  
**Decision:** Phase 3 allows **one position only** (`max_positions: 1`). Multiple
concurrent positions deferred to **Phase 7**.

---

### OQ-17 — Benchmark for comparison
**Priority:** BEFORE PHASE 3  
**Status:** **Resolved → D-42**  
**Decision:** Per-strategy `benchmark: symbol | none`. `symbol` = buy-and-hold the
backtested pair; `none` = skip benchmark for that strategy.

---

### OQ-39 — Sharpe/Sortino on intraday data
**Priority:** PHASE 3  
**Status:** **Resolved → D-46**  
**Decision:** Resample equity to **daily** (UTC) before annualized Sharpe/Sortino when
timeframe is below `1d`.

---

### OQ-40 — Intrabar stop vs signal exit same bar
**Priority:** PHASE 3  
**Status:** **Resolved → D-37**  
**Decision:** Intrabar stop/TP checked first; signal exit at next open only if still open.

---

### OQ-41 — Simultaneous long and short
**Priority:** PHASE 3  
**Status:** **Resolved → D-49**  
**Decision:** One net position only (long **or** short).

---

### OQ-42 — Trailing stop activation bar
**Priority:** PHASE 3  
**Status:** **Resolved → D-41**  
**Decision:** Trailing stop checks start on the **bar after entry**, not the entry bar.

---

### OQ-43 — Risk-based sizing without stop / complete position close
**Priority:** PHASE 3  
**Status:** **Resolved → D-47, D-51**  
**Decision:** (1) Every exit **closes 100% of the open position** — complete
liquidation, no partial exits (D-47). (2) `risk_pct` sizing **requires** a defined
`stop_loss`; otherwise **`ValueError` at startup** (D-51).

---

### OQ-44 — Phase 3 scope
**Priority:** PHASE 3  
**Status:** **Resolved → D-48**  
**Decision:** Full Phase 3 scope in one implementation pass.

---

### OQ-18 — Look-ahead bias enforcement
**Priority:** BEFORE POC  
**Status:** **Resolved → D-14**  
**Question:** How is look-ahead bias prevention enforced as an engine invariant rather
than a convention that callers must remember?  
**Why it matters:** If entry on bar N uses the close of bar N (the signal bar), the
backtest is cheating — that price is not available until the bar closes.  
**Decision:** Entry (and exit) always execute at the open of bar N+1. This is
hardcoded in `engine.py` — not configurable by signal authors. Signal authors have
no mechanism to override it. See D-14 for full reasoning including the final-bar
edge case.

---

## Smart Money Concepts

### OQ-19 — SMC reference framework
**Priority:** BEFORE PHASE 6  
**Question:** Which SMC educator or framework to use as the primary reference?
ICT (Inner Circle Trader), SMC by The Trading Channal, Mentfx, or a synthesis?  
**Why it matters:** SMC terminology and rules differ meaningfully between educators.
ICT's BOS definition differs from others. If the implementation is based on a specific
framework, users aligned with that framework will find it "correct."  
**Decision needed:** Pick one reference per concept or explicitly document the
interpretation used.

---

### OQ-20 — FVG invalidation rules
**Priority:** BEFORE PHASE 6  
**Question:** When is a Fair Value Gap considered "filled" or "invalidated"?  
**Options:**
- When price closes inside the gap (50% fill)
- When price touches the near edge of the gap
- When price fully closes beyond the far edge  
**Why it matters:** Different traders use different fill criteria. The backtesting
behavior changes significantly depending on which rule is used.  
**Decision needed:** Default rule + configurable override before Phase 6.

---

## Screener & Alerts

### OQ-21 — Edge trigger vs level trigger
**Priority:** BEFORE PHASE 7  
**Status:** **Partially resolved → D-52** (backtest entries only)  
**Question:** Should alerts fire every bar the condition is true (level trigger) or
only on the bar the condition *becomes* true (edge trigger)?  
**Backtest decision (D-52):** Entry signals default to **edge**; `entry_trigger: level`
opts into legacy re-entry behavior. Exit signals remain level-triggered.  
**Still open:** Phase 7 screener/alert default and whether exit legs should also be configurable.

---

### OQ-22 — Scan timing relative to candle close
**Priority:** BEFORE PHASE 7  
**Question:** Exactly when does a scheduled scan run? Options:
- At candle close time (derived from timeframe: 1d closes at UTC 00:00)
- Fixed schedule regardless of candle close
- Triggered by new candle insert in the DB  
**Why it matters:** Running a scan before the candle is confirmed (closed) may detect
conditions that the final candle invalidates.  
**Decision needed:** Trigger mechanism for scheduled scans in Phase 7.

---

## DSL Design

### OQ-23 — DSL grammar for AND / OR / NOT
**Priority:** BEFORE PHASE 8  
**Question:** What does the signal dict look like when conditions are combined with
AND / OR / NOT?  
**Draft option A — nested list:**
```json
{
  "entry": {
    "op": "AND",
    "conditions": [
      {"indicator": "RSI", "params": {"period": 14}, "op": "<", "value": 30},
      {"indicator": "SMA", "params": {"period": 200}, "op": "price_above"}
    ]
  }
}
```
**Draft option B — flat array with explicit logic:**
```json
{
  "entry": [
    {"indicator": "RSI", "params": {"period": 14}, "op": "<", "value": 30},
    {"logic": "AND"},
    {"indicator": "SMA", "params": {"period": 200}, "op": "price_above"}
  ]
}
```
**Decision needed:** Pick a schema and document it fully before Phase 8.
Option A (nested tree) is likely cleaner for recursive evaluation.

---

### OQ-24 — Multi-timeframe condition syntax in DSL
**Priority:** BEFORE PHASE 8  
**Question:** How does a condition reference a different timeframe?  
**Draft:**
```json
{
  "indicator": "RSI",
  "params": {"period": 14},
  "timeframe": "1d",
  "op": "<",
  "value": 30
}
```
**Things to consider:** When evaluating an hourly signal, the evaluator must know how
to fetch and align daily candles. Alignment (how many 1h bars map to one 1d bar) must
be handled without look-ahead bias.  
**Decision needed:** Syntax and evaluator behavior before Phase 8.

---

### OQ-25 — Lookback / bar-ago references
**Priority:** BEFORE PHASE 8  
**Question:** How does the DSL express "N bars ago"? Example: "close is higher than
the close 5 bars ago."  
**Draft:**
```json
{"field": "close", "op": ">", "ref": {"field": "close", "bars_ago": 5}}
```
**Decision needed:** Syntax and how the evaluator handles it.

---

## AI Layer

### OQ-26 — LLM choice
**Priority:** BEFORE PHASE 9  
**Question:** Which LLM powers the NL → DSL translation? Options: OpenAI GPT-4o,
Anthropic Claude, local model (Ollama), or pluggable.  
**Things to consider:**
- Quality of JSON generation (structured output mode)
- Cost per translation request
- Whether a local model is good enough to avoid API costs  
**Decision needed:** Before Phase 9. Can be deferred entirely until then.

---

### OQ-27 — Ambiguity handling in NL → DSL
**Priority:** BEFORE PHASE 9  
**Question:** When the user's natural language input is ambiguous (e.g. "buy when RSI
is low" — how low is "low"?), what does the system do?  
**Options:**
- Assume a default and proceed
- Ask the user a clarifying question before generating the signal dict
- Generate multiple interpretations and ask the user to pick  
**Decision needed:** Interaction pattern for the AI layer before Phase 9.

---

### OQ-28 — Prompt engineering strategy
**Priority:** BEFORE PHASE 9  
**Question:** How is the LLM prompted to ensure it generates valid DSL JSON?  
**Things to consider:**
- The LLM must know the exact DSL schema (inject schema into system prompt)
- Structured output / JSON mode reduces hallucination of invalid structure
- Few-shot examples of NL → DSL pairs significantly improve quality  
**Decision needed:** Prompting strategy and validation pipeline before Phase 9.

---

## Infrastructure & Deployment

### OQ-29 — Local-only vs cloud deployment
**Priority:** ANYTIME  
**Question:** Is this platform intended to run locally (developer's machine) or be
deployed to a server/cloud?  
**Why it matters:** Local-only simplifies everything (no auth, no multi-user, no
cloud costs). Cloud deployment requires auth, API security, environment management.  
**Current assumption:** Local-only through Phase 3 at minimum.  
**Decision needed:** Before Phase 7 (screener) where scheduling and always-on
behavior becomes important.

---

### OQ-30 — API design for web layer
**Priority:** BEFORE PHASE 10  
**Question:** What does the REST API look like between the Python backend and the
React frontend?  
**Key endpoints needed:**
- `GET /candles?symbol=BTC/USDT&tf=1d&start=...&end=...`
- `POST /backtest` — accepts strategy dict, returns results
- `POST /scan` — accepts strategy dict, returns matching symbols
- `GET /indicators` — list of available indicators and their params
- `POST /ai/translate` — accepts NL string, returns strategy dict  
**Decision needed:** Full API contract before Phase 10 frontend work begins.

---

### OQ-31 — Derived timeframe performance strategy
**Priority:** BEFORE PHASE 2  
**Question:** Since Phase 1 stores only canonical `1m` candles, when should higher
timeframes be computed on demand versus precomputed with TimescaleDB continuous
aggregates?  
**Why it matters:** On-demand aggregation keeps the system simple and avoids duplicate
stored candles, but repeated `1d`/`1h` reads across many symbols may become slow.
Continuous aggregates can speed common reads, but add schema and refresh complexity.  
**Current assumption:** Derive higher timeframes from `1m` on demand in Phase 1.
Measure before adding continuous aggregates.  
**Decision needed:** Before Phase 2 indicator validation relies heavily on repeated
higher-timeframe reads.

---

## Summary Table

| # | Question | Phase needed by | Status |
|---|---|---|---|
| OQ-01 | Timeframes to store | Phase 1 | Resolved → D-17 |
| OQ-02 | How far back to fetch | Phase 1 | Resolved → D-18 |
| OQ-03 | Exchange source | Phase 1 | Resolved → D-19 |
| OQ-04 | Incremental update logic | Phase 1 | Resolved → D-20 |
| OQ-05 | Data gap handling | Phase 1 | Resolved → D-21 |
| OQ-06 | ClickHouse migration trigger | Phase 7 | Open |
| OQ-07 | RSI smoothing variant | POC | Resolved → D-13 |
| OQ-08 | VWAP variant | Phase 2 | Resolved → D-29 |
| OQ-09 | Indicator param validation | Phase 2 | Resolved → D-30 |
| OQ-32 | Indicator signature convention | Phase 2 | Resolved → D-31 |
| OQ-33 | Multi-output registry design | Phase 2 | Resolved → D-32 |
| OQ-34 | Phase 2 scope | Phase 2 | Resolved → D-33 |
| OQ-35 | Tier 3 deferrals | Phase 2 | Resolved → D-34 |
| OQ-36 | Pivot session boundaries | Phase 2 | Resolved → D-35 |
| OQ-37 | SMA source | Phase 2 | Resolved → D-28 |
| OQ-38 | Ichimoku defaults | Phase 2 | Resolved → D-36 |
| OQ-10 | Swing detection algorithm | Phase 5 | Resolved → D-53 |
| OQ-11 | Equal highs/lows tolerance | Phase 5 | Resolved → D-55 |
| OQ-12 | Multi-TF structure hierarchy | Phase 5 | Resolved → D-58, D-63 |
| OQ-45 | Confirmed vs provisional swings | Phase 5 | Resolved → D-62 |
| OQ-46 | Swing price field | Phase 5 | Resolved → D-53 |
| OQ-47 | S/R zones vs levels | Phase 5 | Resolved → D-57 |
| OQ-48 | Default pivot width | Phase 5 | Resolved → D-53 |
| OQ-49 | Evaluator hook in structure phase | Phase 5 | Resolved → D-63 |
| OQ-50 | Strict pivot rule | Phase 5 | Resolved → D-53 |
| OQ-51 | Vectorbt-style similarity | Phase 5 | Resolved → D-61 |
| OQ-52 | API authentication | Phase 4 | Resolved → D-69 (none) |
| OQ-53 | Replay persistence | Phase 4 | Resolved → D-71, D-78 |
| OQ-54 | Default watchlist | Phase 4 | Resolved |
| OQ-55 | Candle limit | Phase 4 | Resolved → D-79 |
| OQ-56 | Replay step TF | Phase 4 | Resolved |
| OQ-57 | Indicator batching | Phase 4 | Resolved |
| OQ-58 | Live streaming | Phase 4 | Resolved → D-78 (deferred) |
| OQ-13 | Pattern definition reference | Phase 5 | Open |
| OQ-14 | Pattern confidence scoring | Phase 5 | Open |
| OQ-15 | Pattern completion vs formation | Phase 5 | Open |
| OQ-16 | Multiple position rules | Phase 3 | Resolved → D-43 |
| OQ-17 | Backtest benchmark | Phase 3 | Resolved → D-42 |
| OQ-39 | Sharpe on intraday data | Phase 3 | Resolved → D-46 |
| OQ-40 | Stop vs signal same bar | Phase 3 | Resolved → D-37 |
| OQ-41 | Simultaneous long/short | Phase 3 | Resolved → D-49 |
| OQ-42 | Trailing stop start bar | Phase 3 | Resolved → D-41 |
| OQ-43 | Complete position close / risk sizing | Phase 3 | Resolved → D-47, D-51 |
| OQ-44 | Phase 3 scope | Phase 3 | Resolved → D-48 |
| OQ-18 | Look-ahead bias enforcement | POC | Resolved → D-14 |
| OQ-19 | SMC reference framework | Phase 6 | Open |
| OQ-20 | FVG invalidation rules | Phase 6 | Open |
| OQ-21 | Edge vs level trigger | Phase 7 | Partial → D-52 (backtest entries) |
| OQ-22 | Scan timing | Phase 7 | Open |
| OQ-23 | DSL AND/OR/NOT grammar | Phase 8 | Open |
| OQ-24 | Multi-TF DSL syntax | Phase 8 | Open |
| OQ-25 | Lookback syntax in DSL | Phase 8 | Open |
| OQ-26 | LLM choice | Phase 9 | Open |
| OQ-27 | Ambiguity handling | Phase 9 | Open |
| OQ-28 | Prompt engineering strategy | Phase 9 | Open |
| OQ-29 | Local vs cloud deployment | Phase 7 | Open |
| OQ-30 | API design for web layer | Phase 10 | Open |
| OQ-31 | Derived timeframe performance strategy | Phase 2 | Open |

---

## How to Use This Document

1. Before starting any phase, filter the table by "Phase needed by" and resolve all
   open questions for that phase.
2. When a question is resolved, add a numbered decision entry to DECISIONS.md with
   the reasoning, update the status in the summary table to "Resolved → D-XX", and
   optionally move the full question entry to an "Archived" section at the bottom.
3. If a new unresolved question surfaces during implementation, add it here immediately
   with the phase it blocks. Do not start the blocked phase until it is resolved.
