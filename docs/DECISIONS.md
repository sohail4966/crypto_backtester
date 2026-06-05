# Architecture Decision Log

This document captures every significant decision made during the design phase,
the reasoning behind it, and what was explicitly rejected. Its purpose is to avoid
relitigating the same choices and to give future AI sessions or collaborators the
full context in one place.

---

## D-01 — Project scope: what this platform actually is

**Decision:** This is a crypto market analysis and backtesting platform. The core value
is a robust, deterministic trading intelligence engine that understands trading concepts
and can execute them consistently. It is not primarily a charting tool and not primarily
an AI tool.

**Reasoning:** Many traders understand TA but cannot code. The gap is translation —
from idea to executable logic. The platform bridges that gap by having well-defined,
reusable representations of indicators, patterns, and conditions that work the same
way across screening, alerts, backtesting, and AI interaction.

**Rejected framing:** "TradingView with AI" — too broad, implies rebuilding a charting
platform. "AI trading bot" — implies AI is the foundation. Both lead to wrong
build priorities.

---

## D-02 — AI is the last layer, not the foundation

**Decision:** AI (natural language → strategy) is built last, on top of a complete
deterministic engine. Not first, not alongside.

**Reasoning:** AI is only useful if it has a well-defined target to generate. If
indicators, patterns, and strategy rules are not already defined and working, the AI
has nothing concrete to produce. Building AI first creates a system that sounds capable
but cannot execute reliably.

**What AI will do (eventually):** Convert plain English trading ideas into the
structured signal dict (see D-08). Provide post-backtest explanations. Suggest
optimizations. It will not generate executable code — it will generate structured data.

---

## D-03 — Build a vertical slice, not horizontal layers

**Decision:** The POC builds one thin path through all layers end-to-end:
stored candles → indicator → condition → backtest → results.
Not one complete layer at a time.

**Reasoning:** Building each layer "complete" before moving on delays validation,
creates integration surprises, and can waste months before anything runs. A vertical
slice proves the architecture works and every subsequent feature is an extension of
something already working.

---

## D-04 — Local candle storage over live exchange queries

**Decision:** Historical OHLCV data is fetched from exchange APIs once and stored
locally in a database. Backtests and screeners read from local storage, not the
exchange.

**Reasoning:**
- Avoids exchange rate limits during repeated iterations
- Guarantees reproducibility (backtest results are stable over time)
- Required for multi-symbol screening at any reasonable speed
- Enables future timeframe rollups from a single fine-grained source

**Rejected:** Querying ccxt on every backtest run — too slow, rate-limited,
non-reproducible.

---

## D-05 — TimescaleDB now, ClickHouse later

**Decision:** Use TimescaleDB (PostgreSQL + time-series extension) for the POC and
early development. Migrate to ClickHouse when multi-symbol screening becomes the
bottleneck.

**Reasoning for TimescaleDB:**
- It is standard PostgreSQL. Everything learned (SQL syntax, indexing, Python
  connection, psycopg) is universal and transferable.
- Hypertables handle time-based partitioning automatically.
- Lower infra cognitive load than ClickHouse for a learn-as-you-build context.
- Continuous aggregates (1m → 5m → 1h → 1d rollups) are available when needed.

**Reasoning for ClickHouse later:**
- ClickHouse is a columnar OLAP database with a non-standard dialect.
- Its advantages (vectorized scans, extreme compression, sub-second aggregations on
  billions of rows) only appear at scale — thousands of symbols, tick data, or
  large screener queries.
- The migration is cheap because of D-06 (the `get_candles()` boundary) and D-15 (SQL
centralized in `data/repository/`).

**Rejected:** SQLite — doesn't scale to screening; not a real server. ClickHouse from
day one — dialect learning overhead at a stage where it provides no benefit.

---

## D-06 — The `get_candles()` boundary (single most important design rule)

**Decision:** The database is hidden behind one function:

```python
get_candles(symbol: str, timeframe: str, start: str, end: str) -> pd.DataFrame
```

All downstream code (indicators, signals, backtest) reads from a pandas DataFrame.
No layer below the data module is aware of the database technology.

**Reasoning:** This is the swap point for D-05. TimescaleDB → ClickHouse requires
rewriting `data/repository/` (queries + repository) and the row-to-DataFrame mapping in
`loader.py`. Nothing else changes. It also makes indicators and signals independently
testable without a database running.

---

## D-15 — Repository layer for native SQL (Spring-style)

**Decision:** Database access is split: **DDL** in versioned migration files (D-16),
**DML** in `data/repository/queries.py`. Execution goes through repository classes
(e.g. `CandleRepository`) for reads/writes, similar to Spring Data JPA `@Repository`
with `@Query(nativeQuery = true)`.

**Layout:**
- `data/db.py` — connection string and `connect()` only
- `data/migrations/sql/` — versioned DDL applied on startup
- `data/repository/queries.py` — DML constants only; no business logic
- `data/repository/candle_repository.py` — `upsert_many`, `count`, `find_by_date_range`
- `data/storage.py` / `data/loader.py` — thin facades; no inline SQL

**Reasoning:**
- One place to review, diff, and migrate SQL when changing databases (D-05)
- Prevents query strings scattered across modules (common source of drift and bugs)
- Familiar pattern for contributors used to Java/Spring persistence layers
- `get_candles()` remains the public read boundary (D-06); repository is an internal detail

**Rejected:** SQL embedded in `storage.py` and `loader.py` — harder to audit and swap;
duplicates the anti-pattern of SQL in service classes.

---

## D-16 — Versioned SQL migrations on application startup

**Decision:** Database schema is managed with Flyway-style versioned SQL files under
`data/migrations/sql/` (`V001__description.sql`). On every application startup,
`run_migrations()` applies any pending scripts and records them in `schema_migrations`.

**Layout:**
- `data/migrations/sql/` — immutable DDL once applied in an environment
- `data/migrations/migrator.py` — discovers files, orders by version, skips applied
- `data/migrations/queries.py` — SQL for the history table only
- `run_poc.py` → `run_migrations_on_startup()` before fetch/backtest

**Reasoning:**
- Matches Spring Boot + Flyway/Liquibase expectations: schema evolves in order, on boot
- Separates DDL (migrations) from DML (repository queries), per D-15
- Existing databases without `schema_migrations` get migrated forward on next run
  (`CREATE IF NOT EXISTS` in early migrations keeps that safe)

**Rejected:** DDL in `CandleRepository.init_schema()` — no version history, hard to evolve
schema in teams; editing applied SQL in place (Flyway anti-pattern).

---

## D-07 — Indicators are pure functions

**Decision:** Indicator implementations take a pandas Series (or DataFrame) and return
a pandas Series. They have no side effects, no database access, no global state.

```python
def sma(close: pd.Series, period: int) -> pd.Series: ...
def rsi(close: pd.Series, period: int = 14) -> pd.Series: ...
```

**Reasoning:** Pure functions are trivially testable, composable, and reusable across
screening, alerts, and backtesting without modification. Users may request arbitrary
indicator configurations — precomputing and storing indicator values would require
storing every permutation, which is impractical.

**Rejected:** Precomputing and storing indicator values in the database — combinatorial
explosion of parameter combinations, staleness issues, unnecessary storage cost.

---

## D-08 — Signals are structured data (the seed of the DSL)

**Decision:** A trading condition is represented as a plain Python dict (later JSON),
not as executable code. The signal evaluator interprets this structure and computes
entry/exit boolean Series.

```python
{
    "entry": {"indicator": "RSI", "params": {"period": 14}, "op": "<", "value": 30},
    "exit":  {"indicator": "RSI", "params": {"period": 14}, "op": ">", "value": 70},
}
```

**Reasoning:** This is the "SQL for traders" concept in its minimal form. Representing
conditions as data rather than code means:
- AI can generate valid strategies without producing executable code (safer, more
  reliable)
- Conditions can be serialized, stored, versioned, and displayed in a UI
- The evaluator is deterministic and auditable
- AND/OR/nesting can be added by extending the schema, not rewriting consumers

**Rejected:** AI generating Python/Pine Script code directly — fragile, hard to
validate, security risk, tightly coupled to implementation details.

---

## D-09 — numpy deferred

**Decision:** numpy is not used in the POC. pandas rolling functions are sufficient
for SMA and RSI at POC scale.

**Reasoning:** Premature optimization. The POC operates on a single symbol with a few
thousand daily candles. numpy becomes relevant when vectorizing the backtest loop over
many symbols or running it many times for optimization. That is a post-POC concern.

---

## D-10 — POC backtest assumptions

**Decision:** The POC backtest engine is long-only, one position at a time, with
entry and exit at the open of the bar *after* the signal bar, and fixed 100% capital
per trade. Fees, slippage, and stop loss/take profit are not modeled.

**Reasoning:** The goal of the POC backtest is to validate that the pipeline works
end-to-end, not to produce a production-grade simulation. Every real feature (fees,
slippage, sizing, stops) can be added to `engine.py` incrementally once the skeleton
runs. Entering on the next bar's open avoids look-ahead bias, which is a correctness
requirement even in a POC.

---

## D-11 — Pattern detection and SMC are explicitly deferred

**Decision:** Classical chart patterns (Double Top, H&S, Triangles, Flags), candlestick
patterns, divergence detection, and Smart Money Concepts (BOS, CHOCH, FVG, Order
Blocks, Liquidity Sweeps) are all out of scope for the POC.

**Reasoning:**
- Classical patterns have no universally accepted definition. Different traders,
  libraries, and platforms implement them differently. Defining them rigorously is
  a major research and design effort in its own right.
- SMC concepts are even more subjective and trader-dependent.
- None of these are needed to validate the spine (data → indicator → signal → backtest).
- They will be added as modules that produce boolean Series in the same format as
  indicator-based signals, plugging into the existing signal evaluator.

---

## D-12 — First test case: RSI oversold/overbought on BTC/USDT 1d

**Decision:** The first strategy to run is: buy when RSI(14) < 30, sell when RSI(14) > 70,
on BTC/USDT daily data for 2 years.

**Reasoning:** This strategy is simple (one indicator, two thresholds), has a known
behavioral profile (widely discussed online), and is easy to sanity-check. Using a
familiar strategy and a well-known symbol means bugs in the pipeline produce results
that are obviously wrong rather than subtly wrong.

---

---

## D-13 — RSI smoothing method: Wilder's RMA

**Decision:** The RSI implementation uses Wilder's smoothing (RMA — Recursive Moving
Average), not a standard EMA.

**Formula:**
```
rma[0] = mean of first `period` gains/losses
rma[i] = (rma[i-1] * (period - 1) + value[i]) / period
```

**Reasoning:**
- TradingView is the primary sanity-check reference for indicator values. TradingView's
  built-in RSI uses Wilder's smoothing. If a different method is used, the RSI values
  will diverge after the warmup period — making it impossible to cross-check backtest
  signals against TradingView chart annotations.
- Wilder's smoothing is the original definition from J. Welles Wilder Jr.'s 1978 book
  "New Concepts in Technical Trading Systems." It is the de-facto standard for RSI
  across professional platforms (TradingView, Bloomberg, MetaTrader).
- Standard EMA would produce values that look similar but differ by a meaningful amount
  on most bars, silently invalidating any backtests that reference TV screenshots.

**Verification required:** Before trusting any backtest output, load BTC/USDT 1d in
TradingView, read the RSI(14) value for 3–5 specific historical dates, and confirm the
computed values match to at least 2 decimal places. This is a mandatory POC step 3
check.

**Rejected:** Standard EMA (`alpha = 2 / (period + 1)`) — diverges from TradingView
after warmup, breaks the sanity-check reference.

**Resolves:** OQ-07

---

## D-14 — Look-ahead bias prevention: entry at next-bar open is a hardcoded engine invariant

**Decision:** The backtest engine always executes entry and exit at the **open price of
the bar after the signal bar** (bar N+1). This is hardcoded in `engine.py` and is not
configurable by the signal author.

**Concrete rule:**
- Signal computed on bar N using close prices of bars 0…N.
- Entry (or exit) executed at `open[N+1]`.
- The close of bar N is the last price visible to the signal — it is never used as a
  fill price.

**Reasoning:**
- In a live trading context, the signal fires when bar N closes. The earliest possible
  execution is the open of bar N+1. Using `close[N]` as the entry price means buying at
  a price that was only available after the bar was already over — this is look-ahead bias.
- The effect is asymmetric: look-ahead bias inflates wins on momentum moves (you appear
  to have entered at the close, which is the high of a green bar). The backtest looks
  better than it is; live results disappoint.
- Making this a hardcoded invariant rather than a convention means a signal author
  cannot accidentally introduce look-ahead bias by using the wrong price field. The
  engine enforces correctness regardless of what the signal returns.
- This applies to both entry and exit signals. Exit also fires at next-bar open.

**Edge case — final bar:** If the exit signal fires on the last bar of the test window
and there is no bar N+1, the position is closed at the last available price (close of
bar N) and flagged as "open at end of backtest." This is a forced close, not a real
exit; it must be noted in the metrics output.

**Rejected:** Entry at signal-bar close — look-ahead bias, produces unrealistically
good results. Entry at signal-bar high/low — arbitrary and no better than next-bar
open in daily data.

**Resolves:** OQ-18

---

## D-17 — Phase 1 stores canonical 1-minute candles only

**Decision:** Phase 1 stores only `1m` OHLCV candles as canonical market data. Higher
timeframes (`5m`, `15m`, `1h`, `4h`, `1d`, etc.) are derived from the stored `1m`
data instead of being fetched and stored as separate canonical rows.

**Reasoning:**
- A single lowest-granularity source avoids contradictory candles between exchange
  timeframes. All higher timeframes are reproducible from the same base data.
- Future strategies can request multiple timeframes without needing separate exchange
  fetch logic per timeframe.
- This keeps the database model conceptually clean: exchange ingestion owns raw `1m`
  candles, while `get_candles()` can aggregate to the requested timeframe.

**Implementation note:** `get_candles(symbol, timeframe, start, end)` must continue to
be the public boundary. For `timeframe == "1m"`, it reads stored rows directly. For
higher timeframes, it should derive candles from `1m` using SQL aggregation
(`time_bucket` in TimescaleDB) or an equivalent repository method. TimescaleDB
continuous aggregates are an optimization, not the initial source of truth.

**Tradeoff:** This increases initial storage and backfill time compared with storing
only `1d` or `1h`, but it gives the platform the cleanest foundation for backtesting,
screening, and later multi-timeframe logic.

**Resolves:** OQ-01

---

## D-18 — Historical backfill depth is configured per symbol

**Decision:** Initial backfill depth is configured in the sync config as
`symbol -> history`, rather than hardcoded globally.

**Reasoning:** Different symbols have different useful history and listing dates. BTC
and ETH can justify longer histories, while newer assets such as SUI cannot provide
the same depth. Keeping history depth in config makes backfill explicit and easy to
adjust without code changes.

**Implementation note:** Phase 1 will use a separate `data.yaml` for sync settings.
Each configured symbol should declare its quote pair and history depth. If a requested
history starts before the exchange has data, sync should fetch the maximum available
history and log the actual first timestamp stored.

**Resolves:** OQ-02

---

## D-19 — Spot data source: Binance primary, Bybit/OKX fallback

**Decision:** Phase 1 ingests spot candles. Binance is the primary exchange. If
Binance fails for a symbol during sync, the fallback order is Bybit, then OKX.

**Reasoning:** Binance usually has the deepest crypto spot history and liquidity, so
it remains the canonical first choice. Fallbacks make the sync more resilient during
temporary Binance failures, rate-limit issues, or pair-specific API problems.

**Rejected:** Futures/perpetual data in Phase 1. That market has different symbol
semantics, funding, and contract behavior, and should not be mixed with spot candles
in the initial data foundation.

**Resolves:** OQ-03

---

## D-20 — Incremental sync fetches from the prior 1-minute bar and stores only closed candles

**Decision:** Incremental sync starts from `MAX(ts) - 1 bar`, where one bar is one
minute for the canonical stored timeframe. The sync skips the current in-progress
candle and only stores closed candles. Once a closed candle is stored, it is not
overwritten by later exchange responses.

**Reasoning:**
- Starting one bar before `MAX(ts)` protects against pagination boundary issues.
- Skipping in-progress candles keeps stored data stable for backtests.
- Not overwriting closed candles preserves reproducibility. Exchange corrections to
  old OHLCV are rare, and changing historical candles silently would change prior
  backtest results.

**Implementation note:** Upserts for Phase 1 should be careful: duplicate closed
candles can be ignored rather than updated. If an exchange response disagrees with an
already stored closed candle, log it as a data-quality warning for manual review.

**Resolves:** OQ-04

---

## D-21 — Data gaps are persisted and automatically retried

**Decision:** Missing candles are not forward-filled. Gaps are persisted in a
`data_gaps` table for auditing, and the next sync automatically attempts to re-fetch
the missing ranges. If one symbol fails during sync, the job logs the failure and
continues with the remaining symbols.

**Reasoning:**
- Forward-filling OHLCV distorts price and volume and can invalidate indicators.
- Persisting gaps makes data quality inspectable instead of burying it in logs.
- Retrying gaps during later syncs handles transient exchange/API failures without
  requiring manual intervention.
- One bad symbol should not block the rest of the universe.

**Implementation note:** `data_gaps` should track at least `symbol`, `timeframe`,
`start_ts`, `end_ts`, `status`, `retry_count`, `last_checked_at`, and
`last_error`. A gap should be marked resolved when all expected 1-minute candles in
that range are present.

**Resolves:** OQ-05

---

## D-22 — Phase 1 symbol universe is a fixed three-pair USDT spot list

**Decision:** Phase 1 syncs only these USDT spot pairs:

- `BTC/USDT`
- `ETH/USDT`
- `SOL/USDT`

Delisted or unavailable pairs are removed from config manually.

**Reasoning:** A fixed list keeps Phase 1 focused on ingestion correctness rather
than dynamic universe selection. Phase 1 stores canonical `1m` candles, so memory and
disk usage grow quickly with each additional symbol. Limiting the initial universe to
BTC, ETH, and SOL keeps local development practical while still covering the highest
value majors for validating ingestion, gap handling, derived candles, and backtests.

**Rejected:** Rule-based top-N selection by volume in Phase 1. It is useful later for
screening, but dynamic membership complicates reproducibility and backfill operations.
Also rejected for Phase 1: expanding immediately to the broader 10-pair list (`XRP`,
`BNB`, `DOGE`, `TRX`, `ADA`, `SUI`, `AVAX`) because canonical `1m` history would
increase local storage pressure before the data pipeline is proven.

---

## D-23 — Phase 1 sync runs hourly via cron with limited parallelism

**Decision:** Sync is run by cron every hour using `run_sync.py --once`. Backfill and
incremental sync may use limited parallelism, capped at three concurrent symbol jobs,
while still respecting ccxt rate limits.

**Reasoning:** This project is a backtesting platform, not a live-trading engine.
Hourly data freshness is enough for Phase 1, especially because the canonical stored
timeframe is `1m` but downstream use is historical analysis. Cron is simpler and more
operationally transparent than a long-running daemon.

**Implementation note:** The sync runner should continue on per-symbol failures and
emit a final summary of successes, failures, rows inserted, and gaps retried.

---

## D-24 — POC runner no longer fetches data after Phase 1

**Decision:** After Phase 1, `run_poc.py` does not fetch exchange data. It assumes the
sync pipeline has already populated the database. If data is missing, it should fail
with a clear error telling the user to run the sync first.

**Reasoning:** Fetching belongs to the data foundation, not to backtest execution.
Keeping those paths separate prevents `run_poc.py` from becoming a second ingestion
system with different assumptions.

---

## D-25 — Phase 1 uses split configs

**Decision:** Backtest/runtime settings remain in `config.yaml`. Data ingestion
settings move to a separate `data.yaml`.

**Reasoning:** Backtest execution and market data sync have different operational
concerns. Splitting config prevents the single-file POC config from growing into a
mixed-purpose control plane.

---

## D-26 — Sync audit table is deferred, local integration tests are required

**Decision:** A `sync_runs` audit table is deferred out of the Phase 1 MVP. Phase 1
will include local-only integration tests against TimescaleDB, but those tests do not
need to run in CI yet.

**Reasoning:** Gap auditing is required because it affects data correctness. Sync-run
auditing is useful for operations, but logs are enough until ingestion behavior is
stable. Local integration tests give confidence in migrations, repository methods, and
sync behavior without adding CI infrastructure complexity.

---

## Open Questions (not yet decided)

| # | Question | Context |
|---|---|---|
| OQ-06 | TimescaleDB → ClickHouse migration trigger | Decide before Phase 7, once scan performance matters. |
| OQ-08 | VWAP variant | Decide before Phase 2 indicator implementation. |
| OQ-31 | Derived timeframe performance strategy | Higher timeframes are derived from `1m`; decide when to introduce TimescaleDB continuous aggregates versus on-demand aggregation after Phase 1 performance is measured. |
| OQ-23 | Future DSL schema design | As conditions grow (AND/OR, multi-indicator, cross-indicator), the signal dict needs a grammar. Design separately before implementing. |

---

## Platform Pillars (full vision, for orientation)

These are the seven pillars of the full platform. The POC only addresses the first
three at a minimal level. Everything else is future work.

1. **Market data** — OHLCV collection, storage, multi-exchange, multiple timeframes
2. **Indicators** — SMA, EMA, RSI, MACD, ATR, Bollinger Bands, VWAP, volume metrics
3. **Market structure** — swing highs/lows, pivots, trend structure (foundation for patterns and SMC)
4. **Pattern recognition** — classical chart patterns, candlestick patterns, divergence
5. **Strategy and backtesting** — full backtester with fees, slippage, sizing, stops, analytics
6. **AI natural language** — LLM translates plain English → signal dict; strategy gen; post-backtest analysis
7. **Visualization** — chart-based UI, equity curves, pattern overlays

Market structure (pillar 3) is the key enabler for pillar 4. Swing detection → pattern
recognition → divergence detection → SMC are a dependency chain. Do not attempt
pattern recognition without a solid swing detection layer first.
