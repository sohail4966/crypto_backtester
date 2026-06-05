# Phase 1 High Level Design — Data Foundation

**Status:** Planned  
**Prerequisite:** Phase 0 POC complete  
**Next phase after this:** [Phase 2 — Indicator Library](ROADMAP.md#phase-2--indicator-library)

---

## POC Completion Assessment

Phase 0 is **complete**. The repo delivers everything defined in [POC_HLD.md](POC_HLD.md)
and meets the ROADMAP “done when” criterion.

### Success criteria checklist

| Criterion | Status | Evidence |
|---|---|---|
| Single command runs end-to-end | Done | `python run_poc.py` |
| RSI strategy on BTC/USDT 1d | Done | `config.yaml` + `signals/evaluator.py` |
| Printed trade list | Done | `run_poc.py` logs entry/exit dates and return % |
| Summary metrics (win rate, return, drawdown) | Done | `backtest/metrics.py` |
| Equity curve PNG | Done | `output/equity_curve.png` via `save_equity_curve()` |
| Local TimescaleDB storage | Done | Docker Compose + migrations V001–V003 |
| `get_candles()` boundary respected | Done | `data/loader.py`; no SQL outside repository |
| Indicators as pure functions | Done | `indicators/basic.py` — `sma()`, `rsi()` |
| Next-bar open fills (no look-ahead) | Done | `backtest/engine.py` + `tests/backtest/test_engine.py` |
| RSI validated vs TradingView | Done | Regression fixture + 3 date baselines in `tests/indicators/test_basic.py` |

### Build order (POC HLD steps 1–5)

| Step | Status | Notes |
|---|---|---|
| 1. Infra | Done | `docker-compose.yml`, Flyway-style migrator |
| 2. Fetch + store | Done | ccxt pagination, upsert, dedup at batch boundaries |
| 3. Indicators | Done | Wilder RSI; SMA implemented but not used in default strategy |
| 4. Signal evaluator | Done | Dict schema, indicator registry, operator map |
| 5. Backtest + metrics | Done | Long-only, one position, forced close at last bar |

### Rating: **9 / 10** (POC complete, production-minded foundation)

**Breakdown**

| Area | Score | Comment |
|---|---|---|
| Scope delivery | 10/10 | All POC outputs exist and run from one command |
| Architecture | 10/10 | Repository pattern, migrations, `get_candles()` boundary, decision log |
| Code quality | 9/10 | Typed, documented, linted; conventions doc is unusually strong for a POC |
| Testing | 8/10 | 18 unit tests pass; no DB integration test for full pipeline |
| Documentation | 10/10 | POC HLD, ROADMAP, DECISIONS, CONVENTIONS, OPEN_QUESTIONS |
| Operational readiness | 7/10 | Binary fetch (empty vs full history); no incremental updates yet |

**Standout strengths**

- Vertical slice is real — not a stub. Fetch, store, evaluate, backtest, and plot all work.
- Architectural decisions are written down and reflected in code (D-04, D-06, D-14, D-15, D-16).
- Backtest engine correctly implements next-bar open execution and documents forced close.
- Fetcher handles ccxt pagination and duplicate timestamps at batch boundaries.
- RSI uses Wilder's RMA with committed regression baselines — the right validation habit for Phase 2.

**Minor gaps (acceptable for POC, address in Phase 1 or early Phase 2)**

- `ensure_data()` skips network fetch when *any* rows exist — no incremental backfill.
- Default strategy uses RSI 20/80 (not 30/70 from POC HLD); still valid for sanity checks.
- SMA is implemented but has no TradingView regression test (only RSI does).
- No automated end-to-end test against a running TimescaleDB container.
- `years: 3` in config vs “2 years suggested” in docs — harmless, but Phase 1 should make history depth explicit per symbol/timeframe.

**Verdict:** Phase 0 is done. Proceed to Phase 1.

---

## Phase 1 Goal

Make the data layer **production-worthy**: fixed multi-symbol spot coverage, canonical
`1m` storage, reliable incremental updates, gap auditing, and derived higher
timeframes — without changing the public `get_candles()` boundary.

**Done when:** An hourly cron job keeps the approved USDT spot universe current at
`1m` granularity with no manual intervention. Any module can call:

```python
get_candles(symbol, timeframe, start, end) -> pd.DataFrame
```

…and receive clean, up-to-date OHLCV data. For `1m`, this reads stored candles
directly. For higher timeframes, this derives candles from stored `1m` data.

**Explicitly out of scope for Phase 1**

- New indicators (Phase 2)
- Backtest engine changes (Phase 3)
- Multi-symbol screening (Phase 7)
- ClickHouse migration (Phase 7+)
- Web UI, AI, patterns, SMC

---

## Locked Decisions

These Phase 1 blockers are resolved in [DECISIONS.md](DECISIONS.md).

| ID | Decision | Final answer |
|---|---|---|
| OQ-01 | Timeframes for Phase 1 | Store only canonical `1m`; derive higher timeframes |
| OQ-02 | Initial history depth | Configure per symbol in `data.yaml` |
| OQ-03 | Exchange source | Binance spot primary; fallback to Bybit, then OKX |
| OQ-04 | Incremental update logic | Fetch from `MAX(ts) - 1 minute`; skip in-progress candles; do not overwrite closed candles |
| OQ-05 | Gap policy | Persist gaps in `data_gaps`; auto re-fetch gaps on later syncs |

---

## Architecture Changes

Phase 1 extends the data module only. The boundary rule from D-06 stays unchanged.

```
                  ┌────────────────────────────────────────┐
  data.yaml  ──►  │  data/sync.py (NEW)                    │
  cron hourly ─►  │    orchestrates per symbol at `1m`     │
                  └────────────────┬───────────────────────┘
                                   │
                  ┌────────────────▼───────────────────────┐
                  │  data/fetcher.py (EXTEND)              │
                  │    initial fetch + incremental fetch   │
                  │    Binance -> Bybit -> OKX fallback    │
                  └────────────────┬───────────────────────┘
                                   │
                  ┌────────────────▼───────────────────────┐
                  │  data/repository/ (EXTEND)             │
                  │    latest ts, gaps, derived TF queries │
                  └────────────────┬───────────────────────┘
                                   │
                  ┌────────────────▼───────────────────────┐
                  │  data/loader.py (SAME PUBLIC API)      │
                  │    get_candles() direct/derived read   │
                  └────────────────────────────────────────┘
                                   │
              indicators / signals / backtest (UNCHANGED)
```

### New / changed modules

| Module | Action | Purpose |
|---|---|---|
| `data.yaml` | **New** | Sync-only config: exchanges, symbols, history, concurrency |
| `config.yaml` | Keep | Backtest/runtime config only |
| `config.py` | Extend carefully | Keep backtest config; add or delegate sync config parsing |
| `data/fetcher.py` | Extend | `fetch_since()`, closed-candle filtering, exchange fallback |
| `data/repository/queries.py` | Extend | `MAX(ts)`, derived timeframe SQL, gap CRUD |
| `data/repository/candle_repository.py` | Extend | `latest_timestamp()`, `find_gaps()`, derived reads |
| `data/sync.py` | **New** | Sync orchestrator for all configured symbols at `1m` |
| `run_sync.py` | **New** | Cron entry point (`--once`) |
| `data/migrations/sql/V004__data_gaps.sql` | **New** | Persist missing candle ranges for auditing/retry |

### Schema

The existing `candles` table already supports multi-symbol and multi-timeframe via
`(symbol, timeframe, ts)`. Phase 1 uses `timeframe = '1m'` as the only canonical stored
timeframe.

**Required V004** — data gap audit table:

```sql
CREATE TABLE IF NOT EXISTS data_gaps (
    id              BIGSERIAL PRIMARY KEY,
    symbol          TEXT        NOT NULL,
    timeframe       TEXT        NOT NULL,
    start_ts        TIMESTAMPTZ NOT NULL,
    end_ts          TIMESTAMPTZ NOT NULL,
    status          TEXT        NOT NULL, -- open | resolved
    retry_count     INT         NOT NULL DEFAULT 0,
    last_checked_at TIMESTAMPTZ,
    last_error      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at     TIMESTAMPTZ
);
```

`sync_runs` is intentionally deferred out of the Phase 1 MVP.

---

## Config Shape (Phase 1)

Add a new `data.yaml` for ingestion. Keep `config.yaml` for backtest settings only.
Suggested `data.yaml`:

```yaml
timeframe: 1m

exchanges:
  primary: binance
  fallback:
    - bybit
    - okx

quote_currency: USDT

symbols:
  BTC/USDT:
    history: 5y
  ETH/USDT:
    history: 5y
  SOL/USDT:
    history: 5y
  XRP/USDT:
    history: 5y
  BNB/USDT:
    history: 5y
  DOGE/USDT:
    history: 5y
  TRX/USDT:
    history: 5y
  ADA/USDT:
    history: 5y
  SUI/USDT:
    history: 3y
  AVAX/USDT:
    history: 5y

sync:
  mode: cron
  interval_minutes: 60
  max_concurrent_symbols: 3
  store_in_progress_candle: false
  overwrite_closed_candles: false
  retry_gaps: true
```

History depths are examples and should be adjusted before implementation if you want
different symbol-specific windows. `run_sync.py` reads `data.yaml`. `run_poc.py` reads
`config.yaml` and assumes sync has already populated the DB.

---

## Build Order

Each step is independently verifiable. Do not start step N+1 until step N passes.

### Step 1 — Config and symbol list

**Build**

- Add sync config parsing for `data.yaml`.
- Keep `config.yaml` focused on backtest settings.
- Define exactly the approved symbol universe:
  `BTC`, `ETH`, `SOL`, `XRP`, `BNB`, `DOGE`, `TRX`, `ADA`, `SUI`, `AVAX` against USDT.

**Verify**

```bash
pytest tests/config/ -q
python -c "from config import load_config; c=load_config(); print(c)"
python -c "from data.config import load_data_config; c=load_data_config(); print(c)"
```

---

### Step 2 — Repository: latest timestamp and range metadata

**Build**

- Add `SELECT_MAX_TS` to `queries.py`.
- Add `CandleRepository.latest_timestamp(symbol, timeframe) -> datetime | None`.
- Add direct `1m` range reads and derived timeframe reads behind the repository layer.
- Add gap table CRUD methods: create/update/resolve open gaps.

**Verify**

```sql
SELECT symbol, timeframe, COUNT(*), MIN(ts), MAX(ts)
FROM candles
GROUP BY symbol, timeframe;
```

Unit test with mocked cursor; add local-only TimescaleDB integration coverage later.

---

### Step 3 — Incremental 1-minute fetch (`fetch_since`)

**Build**

- Add `fetch_since(symbol, since_ms, exchange_id, timeframe="1m") -> DataFrame`.
- Reuse pagination loop from `fetch_ohlcv`; change the starting `since_ms`.
- Skip the current in-progress candle before returning rows.
- Insert closed candles without overwriting already stored closed candles.
- Try Binance first, then Bybit, then OKX when a symbol fetch fails.

**Incremental logic (recommended)**

1. Read `latest_ts = repository.latest_timestamp(symbol, "1m")`.
2. If `None`: run full initial fetch using that symbol's configured history depth.
3. If set: fetch from `latest_ts - 1 minute`.
4. Drop any in-progress candle from the exchange response.
5. Insert returned closed rows; duplicate closed rows should be ignored.
6. Log rows fetched vs inserted and any duplicate/disagreement warnings.

**Verify**

- Run sync twice for BTC/USDT `1m`; second run should fetch only the boundary range.
- Confirm `MAX(ts)` advances after new closed minutes (or simulate with mocked clock in tests).

---

### Step 4 — Gap detection

**Build**

- Add `find_gaps(symbol, "1m", start, end) -> list[Gap]` in repository.
- Persist missing ranges in `data_gaps`.
- Retry open gaps on each sync before or after the normal incremental fetch.
- Mark a gap resolved when every expected `1m` candle in the range exists.
- Do **not** forward-fill.

**Verify**

- Unit test with synthetic timestamps containing a missing minute.
- Verify an open gap becomes resolved after re-fetch inserts the missing candles.

**Policy**

- `get_candles()` must not forward-fill.
- Sync persists and retries gaps.
- A per-symbol sync failure is logged and skipped; the remaining symbols continue.

---

### Step 5 — Sync orchestrator

**Build**

- `data/sync.py`:
  - `sync_symbol(symbol, history, exchanges) -> SyncResult`
  - `sync_all(config) -> list[SyncResult]`
- Handle per-pair errors without aborting the full run (log and continue).
- Run at most three symbols concurrently.
- Respect ccxt rate limits (`enableRateLimit=True` already set).

**Verify**

```bash
python run_sync.py --once
# Expect: all configured pairs updated, summary logged
```

---

### Step 6 — Scheduler

**Build**

- `run_sync.py` with `--once` for a single cron-triggered pass.
- Document cron example in README:

```cron
0 * * * * cd /path/to/crypto-backtester && .venv/bin/python run_sync.py --once
```

**Verify**

- Let cron run for 24 hours; confirm `1m` candles stay current for all configured symbols.
- Confirm `run_poc.py` fails clearly when required data is missing instead of fetching.

---

### Step 7 — Initial backfill at scale

**Build**

- Script or `run_sync.py --backfill` that walks all configured symbols.
- Use limited parallelism (`max_concurrent_symbols: 3`) while respecting ccxt rate limits.
- Progress logging: `[4/10] ETH/USDT 1m — 1,250,000 rows inserted`.

**Verify**

```sql
SELECT symbol, timeframe, COUNT(*) AS n
FROM candles
GROUP BY 1, 2
ORDER BY 1, 2;
```

Expect non-zero `1m` counts for every configured pair.

---

### Step 8 — Derived timeframe reads

**Build**

- Update the repository/loader path so `get_candles(symbol, "1d", start, end)` derives
  daily candles from stored `1m` rows.
- Support at least the POC `1d` use case before removing fetch logic from `run_poc.py`.
- Keep TimescaleDB continuous aggregates deferred until OQ-31 is resolved.

**Verify**

```bash
python run_poc.py
```

Expected: it reads derived `1d` candles from the database and does not fetch exchange data.

---

## Testing Strategy

| Layer | What to test |
|---|---|
| `fetch_since` | Pagination, empty response, duplicate timestamps |
| `latest_timestamp` | None when empty; correct max when populated |
| Gap detection | Missing bar in synthetic series; clean series returns empty |
| `sync_symbol` | Mock fetcher + repository; verify call sequence |
| Derived timeframes | Known `1m` candles aggregate into expected `1h` / `1d` OHLCV |
| Integration | Local Docker TimescaleDB + one symbol sync end-to-end (mark `@pytest.integration`; not CI) |

Keep indicator and backtest tests unchanged — they prove the boundary still holds.

---

## Phase 1 Done Checklist

- [ ] `data.yaml` contains the approved 10 USDT spot symbols
- [ ] Only canonical `1m` candles are stored for all configured symbols
- [ ] Higher timeframes can be derived through `get_candles()`
- [ ] `run_sync.py --once` completes without manual intervention
- [ ] Hourly cron keeps data current for 24h without errors
- [ ] Incremental sync fetches only new bars (verified by log row counts)
- [ ] Gap detection persists missing ranges in `data_gaps`
- [ ] Open gaps are retried and marked resolved when filled
- [ ] Binance primary plus Bybit/OKX fallback behavior is tested
- [ ] `python run_poc.py` works without fetching exchange data
- [ ] All existing unit tests pass; new data-layer tests added
- [ ] Local-only TimescaleDB integration tests pass
- [ ] Open questions OQ-01 through OQ-05 recorded in DECISIONS.md

---

## What Not to Change

Per D-06, these modules should remain stable during Phase 1:

- `data/loader.py` — public API unchanged
- `indicators/` — no new indicators yet
- `signals/` — no DSL expansion yet
- `backtest/` — no fee/stop/sizing work yet

If you need a new column in `candles`, add `V004__...sql` — never edit applied migrations.

---

## Suggested Implementation Timeline

| Week | Focus |
|---|---|
| 1 | Decisions, `data.yaml`, `latest_timestamp`, `fetch_since`, closed-candle filtering |
| 2 | `data_gaps`, gap retry, exchange fallback, derived `1d` reads |
| 3 | Limited-parallel backfill for 10 symbols, hourly cron, 24h soak test |
| 4 | Local integration tests, README/doc updates, performance notes for OQ-31 |

Adjust based on exchange rate limits; initial backfill of 10 symbols at `1m` granularity
is the longest wall-clock step.

---

## Relationship to Later Phases

| Phase 1 output | Used by |
|---|---|
| Multi-symbol canonical `1m` store | Phase 2 indicator validation across symbols |
| Derived timeframe reads | Phase 2 and Phase 3 multi-timeframe workflows |
| Reliable `get_candles()` | Phase 3 backtests on longer history |
| Gap metadata | Phase 3 trustworthy simulation |
| Sync infrastructure | Phase 7 screener (fresh data for all symbols) |

Phase 2 should not start until the full Phase 1 checklist is complete. Indicator work
depends on stable `get_candles()` behavior and trustworthy derived candles.

---

## References

- [POC_HLD.md](POC_HLD.md) — Phase 0 scope (complete)
- [ROADMAP.md](ROADMAP.md) — Phase 1 summary in platform context
- [DECISIONS.md](DECISIONS.md) — D-04, D-05, D-06, D-15, D-16
- [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) — OQ-01 through OQ-05
- [CONVENTIONS.md](CONVENTIONS.md) — coding rules for all new modules
