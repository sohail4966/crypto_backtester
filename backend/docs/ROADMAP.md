# Platform Roadmap — Crypto Market Analysis & Backtesting Platform

## Vision

A crypto trading analysis platform where traders express ideas in plain English,
and the platform translates those ideas into screening queries, alerts, backtests,
and eventually automated strategies — without requiring the trader to write code.

The platform is built around eight pillars:
1. Market Data
2. Indicators
3. **Client API** (REST + WebSocket — Phase 4)
4. Market Structure
5. Pattern Recognition
6. Strategy & Backtesting
7. AI Natural Language Interface
8. Visualization & UI

Each phase below builds on the previous one. Nothing is throwaway — every module
written in an earlier phase is the literal foundation for the next.

---

## Phase 0 — POC (complete)

**Theme:** Prove the spine works end-to-end on one symbol with one strategy.

**Goal:** A single command runs a backtest, prints metrics, and saves an equity curve.

| Area | What gets built |
|---|---|
| Data | ccxt fetch BTC/USDT 1d, store in TimescaleDB via `CandleRepository` |
| Indicators | `sma()`, `rsi()` as pure functions |
| Signals | Minimal signal dict schema + evaluator |
| Backtest | Long-only, one position, fixed sizing, no fees |
| Output | Trade list, win rate, total return, max drawdown, equity PNG |

**Done when:** `python run_poc.py` produces sensible results for the RSI strategy on BTC/USDT.

**Deliberately excluded:** Everything else.

---

## Phase 1 — Data Foundation

**Status:** Complete. See
[docs/PHASE_1_HLD.md](PHASE_1_HLD.md#phase-1-completion-assessment).

**Theme:** Make the data layer production-worthy. Canonical 1-minute storage,
fixed multi-symbol spot coverage, derived higher timeframes, and reliable incremental
updates.

**Goal:** The data pipeline runs on a schedule and keeps the database current.
Any downstream feature can call `get_candles()` and get clean, up-to-date data.

| Area | What gets built |
|---|---|
| Symbols | Fixed USDT spot universe: BTC, ETH, SOL |
| Timeframes | Store only canonical `1m`; derive higher timeframes from `1m` |
| Incremental updates | Fetch from `MAX(ts) - 1 minute`; skip in-progress candles |
| Data quality | Persist `data_gaps`; auto re-fetch missing ranges; no forward-fill |
| Exchange config | Binance spot primary; fallback to Bybit, then OKX |
| Scheduling | Hourly cron via `run_sync.py --once` |

**Key engineering challenge:** Handling exchange pagination (ccxt `fetch_ohlcv` returns
limited rows per call), keeping closed candles immutable, and deriving higher
timeframes efficiently from canonical `1m` data.

**Done when:** Hourly cron keeps the approved 3-symbol USDT universe current at `1m`
granularity, `get_candles()` can derive higher timeframes, all tests pass, and local
TimescaleDB integration checks pass.

---

## Phase 2 — Indicator Library

**Status:** Complete. See
[docs/PHASE_2_HLD.md](PHASE_2_HLD.md#phase-2-completion-assessment).

**Design doc:** [PHASE_2_HLD.md](PHASE_2_HLD.md)

**Theme:** TA-Lib-backed indicator library with thin wrappers, central registry, and
structural unit tests.

**Goal:** Any common OHLCV-based indicator can be computed from candle data in one
function call and registered for the signal evaluator.

| Area | What was built |
|---|---|
| Engine | TA-Lib wrappers + custom modules under `indicators/custom/` |
| Registry | 58 keys with separate multi-output series (`MACD_HIST`, `BB_UPPER`, …) |
| Evaluator | OHLCV routing via `INDICATOR_META`; `ValueError` → `InvalidSignalError` |
| Validation | Structural tests (params, warmup NaNs, synthetic cases) — no TV baselines (D-28) |
| Tier 1 | SMA, EMA, WMA, MACD, RSI, Bollinger, ATR, ADX, Stochastic, OBV, Volume |
| Tier 2 | SAR, STOCHRSI, CCI, WILLR, MFI, ROC, STDDEV, AD, CMF, BBP + SuperTrend, VWAP, HMA, Keltner, Donchian, Ichimoku, Pivots, Chandelier, volatility/volume indexes, TSI, AO, Qstick |

**Validation approach:** TA-Lib is the reference implementation (D-27, D-28). Tests verify
contracts and correctness properties, not TradingView chart parity.

**Architecture note:** All indicators remain pure functions. Central registry:
```python
from indicators.registry import INDICATORS, INDICATOR_META
```

**Done when:** All in-scope Tier 1 and Tier 2 indicators implemented, registered, tested;
POC `basic.py` removed; full suite green. See
[PHASE_2_HLD.md — Done Criteria](PHASE_2_HLD.md#done-criteria).

---

## Phase 3 — Backtest Engine (full)

**Status:** Complete — [PHASE_3_HLD.md — Completion Assessment](PHASE_3_HLD.md#phase-3-completion-assessment)  
**Rating:** 8.5 / 10

**Theme:** Turn the POC backtest skeleton into a real, reliable simulation engine.

**Goal:** Backtest results are trustworthy enough to make strategy decisions from.

| Area | What was built |
|---|---|
| Fills & costs | `FillModel` / `CostModel` — slippage (bps) + percent/flat commission (D-38, D-39) |
| Sizing | `full_capital`, `fixed_pct`, `fixed_notional`, `risk_pct` with per-side override (D-40, D-51) |
| Risk exits | Fixed + ATR + trailing stops; fixed + risk-reward take profit; intrabar priority (D-37, D-41) |
| Long / short | Dual strategies, one net position (D-49) |
| Metrics | Sharpe, Sortino, Calmar, profit factor; daily equity resample on intraday TFs (D-45, D-46) |
| Benchmark | Per-strategy buy-and-hold `symbol` or `none` (D-42) |
| Export | `output/trades.csv` every run (D-44) |
| Entry trigger | `entry_trigger: edge \| level` on strategies — default edge (D-52) |

**Deferred:** Multiple concurrent positions → Phase 7 (D-43).

**Key correctness requirement:** D-14 — signal fills at next-bar open; intrabar stops use
high/low on the breach bar.

**Done when:** All [Phase 3 done criteria](PHASE_3_HLD.md#done-criteria) pass; full suite
green (`317 passed`). CLI path covered by `test_run_backtest_integration.py`; manual run on synced DB still recommended.

---

## Phase 4 — Client API Layer (REST + WebSocket)

**Status:** Complete — [PHASE_4_HLD.md — Completion Assessment](PHASE_4_HLD.md#phase-4-completion-assessment)  
**Rating:** 8.5 / 10

**Design doc:** [PHASE_4_HLD.md](PHASE_4_HLD.md) · **API spec:** [openapi.yaml](openapi.yaml)

**Theme:** Expose the data and indicator spine to a TradingView-like chart client.
**Historical charts + bar replay only** — no live streaming, no auth.

**Goal:** Client can list symbols, load past candles, compute indicators, manage users/
watchlists, and run **bar replay** over WebSocket with indicators at variable speed.

| Area | What gets built |
|---|---|
| REST | `app.symbols` catalog, historical candles (default 1000 / max 5000), indicators, users, watchlists |
| WebSocket | **Replay only** — play / pause / step / seek + candle + indicator events |
| Users | `name` + `email` in DB; scoped by `user_id` (no passwords) |
| Persistence | `V005`: symbols (3 seeded), users, watchlists |
| Auth | **None** — all routes public (D-69) |

**Deferred to Phase 11:** JWT auth, live candle WebSocket, replay session DB persistence.

**Done when:** ✅ All [Phase 4 done criteria](PHASE_4_HLD.md#done-criteria) pass; `342 passed`
(21 API tests). Manual smoke: `python -m api` → `/docs` → candles + replay WS on synced DB.

---

## Phase 4b — Frontend-Ready API Extensions

**Status:** Complete — [PHASE_4B_HLD.md](PHASE_4B_HLD.md) (API v0.4.1)  
**Prerequisite:** Phase 4 complete  
**Enables:** [SPEC-001](../frontend/docs/SPEC-001.md) chart + replay (D-80, D-81, D-86)

**Theme:** Close the contract gap between Phase 4 and the TradingView-style frontend —
unified chart data, structured symbols, REST replay chunks.

**Goal:** Frontend can load aligned candle + indicator windows in one request and buffer
replay data via REST without a client-side adapter or replay WebSocket.

| Area | What gets built |
|---|---|
| Chart data | `GET /chart-data` — candles + indicators (+ empty signals/trades until 4c) |
| Symbols | `V006` migration — exchange, tick/lot size, asset type; v2 response; `/symbols/search` alias |
| Replay | `POST /replay/runs`, `GET /replay/{run_id}/chunk`, `GET /replay/{run_id}/trades` (stub) |
| Compatibility | Phase 4 REST + replay WS unchanged |

**Deferred:** Workspace sync → **Phase 4d**; backtest HTTP + real trades → **Phase 4c**;
auth / live WS → **Phase 11**.

**Done when:** All [Phase 4b done criteria](PHASE_4B_HLD.md#done-criteria) pass; OpenAPI
and Postman updated; FE can consume `/chart-data` without adapter.

**Follow-up:** [PHASE_4C_HLD.md](PHASE_4C_HLD.md) — Replay V2 (WebSocket streaming,
supersedes REST chunks for replay).

**Follow-up (FE Phase 1 findings):** [PHASE_4B_FE_GAPS.md](PHASE_4B_FE_GAPS.md) —
derived-timeframe `data-range` / `get_latest_candles` fixes so the chart client does not
need 1m metadata fallback workarounds.

---

## Phase 4c — Replay V2 (WebSocket Streaming)

**Status:** Not started — [PHASE_4C_HLD.md](PHASE_4C_HLD.md)  
**Prerequisite:** Phase 4b complete  
**Enables:** [FE Phase 3](../frontend/docs/FE_PHASE_3_HLD.md) replay page

**Theme:** Replace prefix-recompute replay with precomputed rolling buffer + WebSocket
tick batches for near-zero-lag playback.

**Goal:** Open-ended replay from a start anchor over WebSocket; indicators precomputed;
session metadata in Postgres; REST chunk endpoints removed.

| Area | What gets built |
|---|---|
| Replay engine | `ReplayEngine`, `ReplayBuffer`, `OverlayPipeline` |
| Persistence | `V007__replay_sessions.sql`, cursor checkpoint |
| WebSocket | v2 protocol: `snapshot`, `tick_batch`, `buffer_reset` |
| Cleanup | Remove `POST /replay/runs`, `GET /replay/{id}/chunk` |
| Decisions | D-88 through D-94 |

**Done when:** All [Phase 4c done criteria](PHASE_4C_HLD.md#done-criteria) pass.

---

## Phase 5 — Market Structure Detection

**Theme:** Build the structural layer that patterns and SMC depend on. Swing detection
is the prerequisite for classical patterns and liquidity logic.

**Prior design:** Decisions D-53–D-66 and the original Phase 4 HLD content apply here.
A dedicated `PHASE_5_HLD.md` will be written before implementation.

**Goal:** Given a candle series, reliably detect swing highs, swing lows, label trend
structure (HH/HL/LH/LL/EQH/EQL), derive S/R from swings, and expose multi-timeframe context.

| Feature | Notes |
|---|---|
| Swing highs / lows | Symmetric pivot 5/5 (D-53) |
| HH / HL / LH / LL / EQH / EQL | First-class labels (D-65) |
| Support / resistance | Last k swings, recency-first (D-64, D-57) |
| Trend classification | Event-driven on confirmed swings (D-66) |
| Multi-timeframe structure | `StructureContext` forward-fill (D-58) |

**Done when:** Swing points are visually correct on BTC/USDT charts across trending, ranging,
and volatile regimes; `structure/` library + tests complete.

---

## Phase 6 — Pattern Recognition

**Theme:** Detect classical chart patterns and candlestick patterns using the market
structure layer from phase 5.

**Note on difficulty:** Pattern detection is the hardest engineering problem in the
platform. Classical patterns have no single universal definition. Every implementation
is an approximation. Expect iteration and configurable thresholds.

### 5a — Candlestick Patterns (easier, well-defined)

| Pattern |
|---|
| Bullish / Bearish Engulfing |
| Hammer / Inverted Hammer |
| Shooting Star |
| Doji (standard, gravestone, dragonfly) |
| Morning Star / Evening Star |
| Three White Soldiers / Three Black Crows |
| Harami |

### 5b — Classical Chart Patterns (harder, require swing layer)

| Pattern | Notes |
|---|---|
| Double Top / Double Bottom | Two swings at similar price levels |
| Head and Shoulders / Inverse | Three-swing structure with neckline |
| Ascending / Descending / Symmetrical Triangle | Converging trendlines |
| Bull Flag / Bear Flag | Impulse + consolidation channel |
| Pennant | Impulse + converging consolidation |
| Wedge (rising / falling) | Converging trendlines with slope bias |
| Cup and Handle | Rounded bottom + small pullback |

### 5c — Divergence Detection

| Type | Notes |
|---|---|
| RSI Regular Divergence | Price higher high, RSI lower high (bearish) / reverse (bullish) |
| RSI Hidden Divergence | Price higher low, RSI lower low (bullish continuation) |
| MACD Divergence | Same logic applied to MACD histogram |
| Stochastic Divergence | Same logic applied to stochastic |

**Architecture note:** All patterns output the same format as indicator-based signals —
a boolean Series with optional metadata (pattern start bar, end bar, key price levels).
The signal evaluator treats them identically.

**Reference (investigate later):** [vectorbt PRO](https://vectorbt.pro/tutorials/patterns-and-projections/)
uses a different approach from our planned rule-based patterns. It scans price windows
with `find_pattern()` / `PatternRanges.from_pattern_search()`: rescale a numeric
template (shape or recent price slice), score element-wise similarity (Numba, no ML),
keep matches above a threshold, then optionally project forward paths from historical
matches. Candlestick tutorials often pair **TA-Lib `CDL*`** with vectorbt for
backtesting — that path is rule-based like 5a, not PRO’s similarity search. Worth
reviewing before Phase 5 for projections and sweep performance; our spine still
targets explicit swing + pattern rules (Phase 5 → 6).

**Done when:** Each pattern is detectable, produces minimal false positives on clean
historical data, and outputs standard signal format.

---

## Phase 7 — Smart Money Concepts (SMC)

**Theme:** Add SMC-based market structure analysis for traders who use that framework.

**Note on subjectivity:** SMC definitions vary significantly between traders and
educators. All implementations will be configurable and clearly documented as one
specific interpretation. Users should be able to adjust parameters.

| Concept | Notes |
|---|---|
| Break of Structure (BOS) | Price breaks past a prior swing high/low with intent |
| Change of Character (CHOCH) | First BOS in the opposite direction; trend shift signal |
| Fair Value Gap (FVG) | Three-candle imbalance; bullish and bearish variants |
| Order Block | Last up/down candle before a strong impulse move |
| Liquidity Sweep | Price briefly breaks a swing level and reverses (stop hunt) |
| Breaker Block | Failed order block that flips role |
| Mitigation Block | Order block that gets partially mitigated |

**Done when:** Each concept is detectable on BTC/USDT, configurable, and integrated
into the signal evaluator as a named condition.

---

## Phase 8 — Screener & Alert Engine

**Theme:** Apply the signal evaluator across many symbols simultaneously. This is
where TimescaleDB → ClickHouse migration becomes worth doing.

**Goal:** "Show me all coins where RSI(14) < 30 on the daily and price is above SMA(200)"
runs in seconds across 100+ symbols.

| Feature | Notes |
|---|---|
| Multi-symbol scan | Run a signal dict against all tracked symbols |
| Multi-timeframe scan | Scan on 1h, 4h, and 1d simultaneously |
| Condition combinations | AND / OR logic in the signal dict (DSL extension) |
| Alert triggers | Detect when a condition *becomes* true (edge trigger vs level trigger) |
| Alert delivery | Console first; email/webhook/Telegram later |
| Scheduled scans | Run every candle close on configured timeframes |
| Scan results storage | Save scan history for tracking when signals appeared |

**DB migration note (TimescaleDB → ClickHouse):** If scan performance is the bottleneck
at this phase, migrate the `candles` table to ClickHouse. Because of D-06, only
`data/repository/` and `loader.py` change. Evaluate actual performance before migrating — Timescale may
be sufficient.

**Done when:** A scan across 50+ symbols on two timeframes completes in under 10
seconds and alert triggers fire correctly on candle close.

---

## Phase 9 — Full Trading DSL

**Theme:** Formalize the signal dict into a real grammar that can express any
combination of conditions.

**Goal:** The DSL is expressive enough to represent 95% of strategies traders describe
in plain English, and strict enough to be reliably generated by an LLM.

| Feature | Notes |
|---|---|
| AND / OR / NOT logic | Combine multiple conditions |
| Cross-indicator conditions | e.g. RSI > SMA of RSI |
| Multi-timeframe conditions | e.g. daily trend is up AND hourly RSI < 40 |
| Lookback references | e.g. close > close[5] (5 bars ago) |
| Sequence conditions | e.g. pattern A followed by pattern B within N bars |
| Named strategy library | Save, name, and reload strategy definitions |
| DSL versioning | Schema version field for forward compatibility |

**This phase is the bridge to the AI layer.** The DSL schema becomes the exact output
format the LLM is prompted to generate. Every token the LLM writes maps to a
deterministic computation in the evaluator.

**Done when:** The DSL can express at minimum: any single-indicator condition, any
multi-indicator AND/OR condition, any pattern + indicator combination, and any
multi-timeframe condition.

---

## Phase 10 — AI Natural Language Interface

**Theme:** Allow traders to describe a strategy in plain English and have it
translated into a valid DSL signal dict.

**Goal:** A trader types "buy when the daily RSI is oversold and price is above the
200 SMA, sell when RSI goes overbought" and gets a backtest result.

| Feature | Notes |
|---|---|
| NL → DSL translation | LLM takes free text, returns signal dict JSON |
| Validation layer | Signal dict is validated against DSL schema before execution |
| Clarification loop | If translation is ambiguous, ask the user to confirm before running |
| Context awareness | LLM knows what indicators, patterns, and timeframes are available |
| Strategy explanation | Given a signal dict, explain it back in plain English |
| Backtest narrative | After a backtest, explain why it performed well or poorly |
| Strategy suggestions | Given an asset and timeframe, suggest strategies to explore |

**Key design principle:** The LLM generates data (JSON), not code. The backtest engine
remains fully deterministic. AI is a translation layer only.

**Done when:** A non-technical trader can describe a strategy, run it, and get results
without touching any config file or code.

---

## Phase 11 — Visualization & Web UI

**Theme:** TradingView-like chart client consuming the Phase 4 API. Focused tool for
analysis, screening, and backtesting — not a full TradingView clone.

| Feature | Notes |
|---|---|
| Candle charts | Historical load via Phase 4 REST |
| Indicator overlays | Phase 4 `/indicators/compute` + replay WS |
| Bar replay UI | Phase 4 replay WebSocket |
| Watchlists | Phase 4 user/watchlist APIs (`user_id`, no auth yet) |
| **Auth (JWT)** | **Phase 11** — wrap existing user table |
| **Live chart tail** | **Phase 11** — WebSocket after sync |
| **Replay persistence** | **Phase 11** — `app.replay_sessions` table |
| Signal markers | Show entry / exit points on chart (backtest API stretch) |
| Pattern overlays | Phase 6+ structure/pattern endpoints |
| Backtest results UI | Equity curve, trade list, metrics dashboard |
| Screener UI | Phase 8 conditions |
| Strategy builder UI | Visual condition builder (pre-AI) |
| Strategy chat | Phase 10 AI chat interface |
| Alert management | Phase 8 alerts |

**Frontend:** React + TypeScript. **Backend:** Phase 4 FastAPI (extend with later phases).

**Done when:** Core workflows (create user → watchlist → historical chart + indicators →
bar replay → backtest results) work in a browser. Login optional until Phase 11 auth ships.

---

## Dependency Map

```
Phase 0 (POC)
    └── Phase 1 (Data)
            └── Phase 2 (Indicators)
                    ├── Phase 3 (Backtest engine)
                    │       └── Phase 10 (AI) ← depends on Phase 9 DSL
                    ├── Phase 4 (Client API — REST + WS)
                    │       └── Phase 11 (Web UI)
                    ├── Phase 5 (Market structure)
                    │       ├── Phase 6 (Patterns)
                    │       │       └── Phase 7 (SMC)
                    │       └── Phase 8 (Screener) ← also needs Phase 2, 4
                    └── Phase 9 (DSL)
                            └── Phase 10 (AI)
```

Phases 4, 5, and 8 can be developed in parallel once Phase 2 is stable (Phase 4 only
needs Phases 1–2; no backtest dependency).
Phase 9 (DSL) can be designed in parallel with Phases 5–7 and formalized once
the full set of signal types is known.
Phase 11 (UI) starts once Phase 4 API contracts are stable; features accrete as
Phases 5–10 complete.

---

## What This Is Not

- Not a live trading / execution platform (no order placement, no broker integration)
- Not a copy-trading or signal subscription service
- Not a portfolio tracker
- Not a full TradingView replacement (no social, no script marketplace, no drawing sync cloud)

Phase 4 adds **historical chart APIs** and **bar replay** — not live exchange feeds.
Live streaming and auth ship in Phase 11.

These may be future phases but are not part of the current vision.

---

## Phase Summary Table

| Phase | Theme | Key output | Prerequisite |
|---|---|---|---|
| 0 | POC | Backtest one strategy on BTC/USDT | — |
| 1 | Data foundation | Multi-symbol, multi-TF, incremental updates | Phase 0 |
| 2 | Indicator library | Full validated indicator set | Phase 1 |
| 3 | Full backtest engine | Fees, stops, sizing, full metrics | Phase 2 |
| 4 | Client API | REST + replay WS: candles, indicators, users, watchlists | Phases 1, 2 | **Complete** (8.5/10) |
| 5 | Market structure | Swing detection, trend labeling | Phase 2 |
| 6 | Pattern recognition | Chart patterns, candles, divergence | Phase 5 |
| 7 | SMC | BOS, CHOCH, FVG, Order Blocks | Phase 5 |
| 8 | Screener & alerts | Multi-symbol scans, alert triggers | Phases 2, 3, 4 |
| 9 | Full DSL | AND/OR, multi-TF, sequence conditions | Phases 6, 7, 8 |
| 10 | AI NL interface | Plain English → backtest results | Phase 9 |
| 11 | Web UI | Browser chart client on Phase 4 API | Phase 4 |
