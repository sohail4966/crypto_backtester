# Platform Roadmap — Crypto Market Analysis & Backtesting Platform

## Vision

A crypto trading analysis platform where traders express ideas in plain English,
and the platform translates those ideas into screening queries, alerts, backtests,
and eventually automated strategies — without requiring the trader to write code.

The platform is built around seven pillars:
1. Market Data
2. Indicators
3. Market Structure
4. Pattern Recognition
5. Strategy & Backtesting
6. AI Natural Language Interface
7. Visualization & UI

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

## Phase 4 — Market Structure Detection

**Design doc:** [PHASE_4_HLD.md](PHASE_4_HLD.md) (approved — ready for implementation)

**Theme:** Build the structural layer that everything else depends on. Swing detection
is the prerequisite for patterns, divergence, and SMC.

**Goal:** Given a candle series, reliably detect swing highs, swing lows, pivots,
and higher-level trend structure.

| Feature | Notes |
|---|---|
| Swing highs / lows | Configurable lookback (e.g. 5-bar pivot) |
| Higher highs / lower lows | Trend structure labeling |
| Pivot levels | Support / resistance zones derived from swings |
| Trend classification | Uptrend, downtrend, ranging per timeframe |
| Multi-timeframe structure | Daily structure vs hourly structure |

**Why this phase is its own thing:** Swing detection algorithms have many variants and
edge cases (what counts as a "significant" swing, how to handle equal highs, how to
label structure in choppy markets). Getting this right takes iteration. It is the
foundation for phase 5, so it must be solid before patterns are attempted.

**Done when:** Swing points are visually correct on BTC/USDT charts across multiple
market conditions (trending, ranging, volatile).

---

## Phase 5 — Pattern Recognition

**Theme:** Detect classical chart patterns and candlestick patterns using the market
structure layer from phase 4.

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
targets explicit swing + pattern rules (Phase 4 → 5).

**Done when:** Each pattern is detectable, produces minimal false positives on clean
historical data, and outputs standard signal format.

---

## Phase 6 — Smart Money Concepts (SMC)

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

## Phase 7 — Screener & Alert Engine

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

## Phase 8 — Full Trading DSL

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

## Phase 9 — AI Natural Language Interface

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

## Phase 10 — Visualization & Web UI

**Theme:** Give the platform a usable interface. Not a TradingView clone — a focused
tool for analysis, screening, and backtesting.

| Feature | Notes |
|---|---|
| Candle charts | Interactive OHLCV charts (lightweight-charts or Recharts) |
| Indicator overlays | SMA, EMA, BB on the chart |
| Signal markers | Show entry / exit points on chart |
| Pattern overlays | Show detected patterns on chart |
| Backtest results UI | Equity curve, trade list, metrics dashboard |
| Screener UI | Input conditions, see matching symbols |
| Strategy builder UI | Visual condition builder (pre-AI) |
| Strategy chat | AI chat interface for NL → strategy |
| Alert management | View, configure, and manage active alerts |

**Backend:** FastAPI serving existing Python modules as API endpoints.
**Frontend:** React + TypeScript. Charts via `lightweight-charts` (TradingView's
open-source library).

**Done when:** Core workflows (fetch data → run backtest → see results on a chart)
are usable in a browser.

---

## Dependency Map

```
Phase 0 (POC)
    └── Phase 1 (Data)
            └── Phase 2 (Indicators)
                    ├── Phase 3 (Backtest engine)
                    │       └── Phase 9 (AI) ← depends on Phase 8 DSL
                    ├── Phase 4 (Market structure)
                    │       ├── Phase 5 (Patterns)
                    │       │       └── Phase 6 (SMC)
                    │       └── Phase 7 (Screener) ← also needs Phase 2
                    └── Phase 8 (DSL)
                            └── Phase 9 (AI)
                                    └── Phase 10 (UI)
```

Phases 3, 4, and 7 can be developed in parallel once Phase 2 is stable.
Phase 8 (DSL) can be designed in parallel with Phases 4–6 and formalized once
the full set of signal types is known.
Phase 10 (UI) can begin in parallel with Phase 9 — the API layer can be wired up
as modules complete.

---

## What This Is Not

- Not a live trading / execution platform (no order placement, no broker integration)
- Not a copy-trading or signal subscription service
- Not a portfolio tracker
- Not a TradingView replacement (no real-time streaming charts)

These may be future phases but are not part of the current vision.

---

## Phase Summary Table

| Phase | Theme | Key output | Prerequisite |
|---|---|---|---|
| 0 | POC | Backtest one strategy on BTC/USDT | — |
| 1 | Data foundation | Multi-symbol, multi-TF, incremental updates | Phase 0 |
| 2 | Indicator library | Full validated indicator set | Phase 1 |
| 3 | Full backtest engine | Fees, stops, sizing, full metrics | Phase 2 |
| 4 | Market structure | Swing detection, trend labeling | Phase 2 |
| 5 | Pattern recognition | Chart patterns, candles, divergence | Phase 4 |
| 6 | SMC | BOS, CHOCH, FVG, Order Blocks | Phase 4 |
| 7 | Screener & alerts | Multi-symbol scans, alert triggers | Phases 2, 3 |
| 8 | Full DSL | AND/OR, multi-TF, sequence conditions | Phases 5, 6, 7 |
| 9 | AI NL interface | Plain English → backtest results | Phase 8 |
| 10 | Web UI | Full browser-based platform | Phases 3, 9 |
