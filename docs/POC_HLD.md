# POC High Level Design — Crypto Backtester

## Goal

Prove that a trading idea expressed as a structured condition can be evaluated against
locally-stored crypto candle data and backtested into real performance metrics.

No AI. No charts. No pattern recognition. Just the spine.

## Success Criteria

The POC is complete when a single command produces:

- A backtest of a simple RSI-based strategy on BTC/USDT daily data
- Printed trade list (entry date, exit date, return per trade)
- Summary metrics: win rate, total return, max drawdown
- Equity curve saved as a PNG

## What Is Explicitly Out of Scope

| Feature | Reason deferred |
|---|---|
| AI / natural language input | Last layer; requires the deterministic engine first |
| Chart / UI / web frontend | Not needed to prove the core pipeline |
| Pattern detection (H&S, Double Top, etc.) | No universal definition; major rabbit hole |
| Smart Money Concepts (BOS, CHOCH, FVG) | Even more subjective; post-POC |
| Divergence detection | Post-POC |
| Multi-symbol screening | Post-POC; this is where ClickHouse pays off |
| Real-time / live data | Post-POC |
| Multi-exchange support | Post-POC |
| Stop loss / take profit / slippage / commissions | Post-POC backtest features |
| numpy | Defer until a hot loop proves too slow |
| ClickHouse | Deferred; replace TimescaleDB when screening becomes the bottleneck |


## Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Language | Python 3.11+ | Best ecosystem for this domain |
| Exchange data | ccxt | Unified API for Binance and others |
| Data wrangling | pandas | Candle DataFrames, rolling windows |
| Database | TimescaleDB (PostgreSQL extension) | Time-series hypertable; plain SQL syntax |
| DB driver | psycopg3 or SQLAlchemy | Connect Python to Timescale |
| Plotting | matplotlib | Save equity curve as PNG |
| Runtime | Docker Compose | Run TimescaleDB locally without installing Postgres |

## Architecture

```
crypto-backtester/
├── data/
│   ├── fetcher.py        # ccxt: download OHLCV candles from exchange
│   ├── db.py             # connection helpers (no SQL)
│   ├── migrations/
│   │   ├── sql/          # V001__*.sql versioned DDL (Flyway-style)
│   │   └── migrator.py   # runs pending migrations on application startup
│   ├── repository/
│   │   ├── queries.py    # DML only (like JPA @Query nativeQuery)
│   │   └── candle_repository.py  # executes queries; one repo per table/aggregate
│   ├── storage.py        # startup migrations + write facade
│   └── loader.py         # get_candles() -> pandas DataFrame  ← the key boundary
├── indicators/
│   └── basic.py          # pure functions: sma(), rsi()
├── signals/
│   └── evaluator.py      # evaluate a condition dict -> entry/exit boolean Series
├── backtest/
│   ├── engine.py         # walk bars, open/close positions, record trades
│   └── metrics.py        # win rate, total return, max drawdown, equity curve
├── run_poc.py             # wires everything together; entry point
├── docker-compose.yml     # TimescaleDB service
├── requirements.txt
└── docs/
    ├── POC_HLD.md         # this file
    └── DECISIONS.md       # all architectural decisions and their rationale
```

## The One Rule That Matters

Everything downstream of the database reads candles through a single function:

```python
get_candles(symbol: str, timeframe: str, start: str, end: str) -> pd.DataFrame
```

The DataFrame always has columns: `ts, open, high, low, close, volume`.

Indicators, signals, and the backtest engine never touch the database directly.
Swapping TimescaleDB for ClickHouse later touches `data/repository/` (queries + repository)
and the thin mapping in `loader.py`. Nothing else changes.

## Data Layer

### Repository pattern

DML is defined in `data/repository/queries.py` and executed by `CandleRepository`
(analogous to a Spring Data `JpaRepository` with `nativeQuery = true`). `loader.py` maps
rows to pandas — it must not contain inline SQL.

### Database migrations (startup)

DDL is versioned under `data/migrations/sql/` as `V{version}__{description}.sql` and applied
on every application startup via `run_migrations()` (like Flyway). Applied versions are
recorded in `schema_migrations`. `run_poc.py` calls this before any fetch or backtest.

| Migration | Purpose |
|-----------|---------|
| V001 | `schema_migrations` history table |
| V002 | `candles` table |
| V003 | Timescale hypertable on `candles.ts` |

Do not change SQL files after they have been applied in any environment; add a new `V004__...`
file instead.

### TimescaleDB Table

Created by migration `V002__create_candles_table.sql`:

```sql
CREATE TABLE IF NOT EXISTS candles (
    symbol     TEXT             NOT NULL,
    timeframe  TEXT             NOT NULL,
    ts         TIMESTAMPTZ      NOT NULL,
    open       DOUBLE PRECISION NOT NULL,
    high       DOUBLE PRECISION NOT NULL,
    low        DOUBLE PRECISION NOT NULL,
    close      DOUBLE PRECISION NOT NULL,
    volume     DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (symbol, timeframe, ts)
);
```

Hypertable: `V003__create_candles_hypertable.sql` → `create_hypertable('candles', 'ts', ...)`.

### Why local storage instead of querying the exchange every time

- Avoids rate limits during repeated backtesting iterations
- Ensures reproducibility (exchange history can change)
- Required for future screening across many symbols at speed
- Foundation for continuous aggregate rollups (1m → 5m → 1h → 1d) later

## Indicator Layer

Indicators are **pure functions**. They take a pandas Series (or DataFrame) and return
a pandas Series. They have no knowledge of the database or the signal layer.

```python
def sma(close: pd.Series, period: int) -> pd.Series:
    return close.rolling(period).mean()

def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    # Wilder's smoothing (same as TradingView)
    ...
```

Validation approach: manually check a few values against TradingView for BTC/USDT 1d
before trusting the output in a backtest.

## Signal Layer

A signal is a plain Python dict (later JSON). It describes a condition without being
executable code. This is the seed of the future trading DSL and the eventual target
that the AI layer will generate.

```python
strategy = {
    "entry": {"indicator": "RSI", "params": {"period": 14}, "op": "<", "value": 30},
    "exit":  {"indicator": "RSI", "params": {"period": 14}, "op": ">", "value": 70},
}
```

The evaluator resolves the indicator, applies params, and returns a boolean Series for
entry and exit independently. No string eval, no code generation — pure data.

## Backtest Engine

- **Style:** long-only, one position at a time
- **Entry:** open price of the bar *after* the signal bar (avoid look-ahead bias)
- **Exit:** open price of the bar after the exit signal
- **Position sizing:** fixed 100% of capital per trade (simplest for POC)
- **Fees / slippage:** not modeled in POC

Each trade records: entry date, exit date, entry price, exit price, return (%).

## Metrics

| Metric | Definition |
|---|---|
| Total return | Final equity / initial capital - 1 |
| Win rate | Winning trades / total trades |
| Max drawdown | Largest peak-to-trough decline in equity curve |
| Equity curve | Cumulative value of capital over time, saved as PNG |

## Build Order

Each step is independently runnable and verifiable before the next begins.

1. **Infra** — Docker Compose up with TimescaleDB; connect from Python; create hypertable.
   *Verify:* `SELECT version()` and `SELECT * FROM timescaledb_information.hypertables`.

2. **Fetch + store** — ccxt fetch BTC/USDT 1d for 2 years; insert into `candles`.
   *Verify:* `SELECT COUNT(*), MIN(ts), MAX(ts) FROM candles`.

3. **Indicators** — implement `sma()` and `rsi()`; load candles via `get_candles()`.
   *Verify:* print last 5 rows of each series; spot-check 3 values against TradingView.

4. **Signal evaluator** — parse the strategy dict; call indicators; return entry/exit Series.
   *Verify:* print all dates where entry signal is True.

5. **Backtest + metrics** — run the loop; print trade list and summary; save equity PNG.
   *Verify:* numbers are directionally sane (compare manually for 1-2 trades).

## First Strategy to Test (for validation only)

> Buy BTC/USDT when RSI(14) drops below 30. Sell when RSI(14) rises above 70.

This is a well-known oversold/overbought strategy. Its historical performance on BTC is
widely discussed online, so you have a sanity-check benchmark. It is **not** expected
to be profitable — it just needs to produce results that are explainable.

## How POC Grows Into the Full Platform

| Future feature | Plugs in here |
|---|---|
| More indicators (MACD, ATR, BB, VWAP) | New functions in `indicators/` |
| Patterns, divergence, SMC | New modules that also return boolean Series |
| Full DSL (AND/OR/nesting) | Extend the signal dict schema in `signals/` |
| Multi-symbol screening | Run `evaluator.py` across N symbols; swap DB to ClickHouse |
| Alerts | Evaluate signals on latest bar; push notification |
| Stop loss / take profit / sizing models | Extend `backtest/engine.py` |
| AI natural language → strategy | LLM outputs the strategy dict; everything else unchanged |
| Web UI / charts | FastAPI backend + React frontend consuming backtest results |

Nothing built in the POC is throwaway. Each module is the literal starting point for
the corresponding pillar in the full platform.
