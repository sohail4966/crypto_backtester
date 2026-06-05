# Crypto Backtester (Phase 0 POC)

A Python backtesting spine for crypto: fetch OHLCV candles, store them locally, evaluate
indicator-based strategy rules, and simulate long-only trades with performance metrics.

This is **Phase 0** of a larger platform (see [docs/ROADMAP.md](docs/ROADMAP.md)). The POC
proves one path end-to-end: **BTC/USDT daily** data, **RSI(14)** oversold/overbought strategy,
printed trade log, summary metrics, and an equity curve PNG.

## What it does

```
Exchange (Binance via ccxt) → TimescaleDB → get_candles() → indicators → signals → backtest → output
```

- **No AI, UI, or pattern detection** in this phase — only the deterministic pipeline.
- **One design rule:** everything below the database reads candles through `get_candles()` so
  the DB can be swapped later without touching indicators, signals, or the engine.
- **SQL rule:** DDL in `data/migrations/sql/` (versioned, run on startup); DML in
  `data/repository/queries.py`. Repositories execute DML; facades do not embed queries.

### Database migrations

On every `run_poc.py` startup, pending migrations in `data/migrations/sql/` are applied
automatically (like Flyway/Liquibase):

| File | Purpose |
|------|---------|
| `V001__schema_migrations.sql` | History table |
| `V002__create_candles_table.sql` | OHLCV table |
| `V003__create_candles_hypertable.sql` | Timescale hypertable |

Add `V004__your_change.sql` for schema changes — never edit applied migration files.

## Prerequisites

- Python **3.11+**
- [Docker](https://docs.docker.com/get-docker/) (for TimescaleDB)
- Network access for the first historical fetch (Binance via ccxt)

## Quick start

```bash
# 1. Start TimescaleDB (port 5433 — avoids conflict with local Postgres on 5432)
docker compose up -d

# 2. Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Optional: override DB URL (copy from example)
cp .env.example .env

# 4. Run the POC
python run_poc.py
```

**First run** applies DB migrations, fetches ~2 years of BTC/USDT 1d candles, runs the backtest,
logs results, and writes `output/equity_curve.png`.

**Later runs** reuse stored candles (no re-fetch unless the table is empty).

## Configuration

| Source | Purpose |
|--------|---------|
| [config.yaml](config.yaml) | Symbol, timeframe, years, exchange, capital, strategy rules, output paths |
| [data.yaml](data.yaml) | Ingestion settings for Phase 1 sync (symbols, exchanges, schedule, retry policy) |
| `.env` | Secrets and overrides (`DATABASE_URL`) — never commit this file |

Example strategy in `config.yaml` (validation only, not expected to be profitable):

- **Entry:** RSI(14) &lt; 30  
- **Exit:** RSI(14) &gt; 70  

Edit `config.yaml` to change the pair, lookback, or thresholds. See [docs/POC_HLD.md](docs/POC_HLD.md)
for architecture details.

## Data sync (Phase 1)

`run_sync.py` performs one ingestion pass and exits:

```bash
python run_sync.py --once
```

Cron example (hourly):

```cron
0 * * * * cd /path/to/crypto-backtester && .venv/bin/python run_sync.py --once
```

## Project layout

```
crypto-backtester/
├── config.yaml           # App settings (non-secret)
├── config.py             # Loads YAML + .env
├── data.yaml             # Phase 1 ingestion/sync settings
├── run_poc.py            # CLI entry point
├── run_sync.py           # Phase 1 sync entry point (cron-friendly --once)
├── data/
│   ├── fetcher.py        # ccxt download
│   ├── db.py             # connection only (no SQL)
│   ├── migrations/
│   │   ├── sql/          # V001__*.sql, V002__*.sql (Flyway-style)
│   │   └── migrator.py   # applied on startup via run_poc.py
│   ├── repository/
│   │   ├── queries.py    # DML only (SELECT/INSERT)
│   │   └── candle_repository.py  # Spring-style repo; runs queries
│   ├── storage.py        # migrations + write facade
│   └── loader.py         # get_candles() — read boundary → repository
├── indicators/
│   └── basic.py          # sma(), rsi() (Wilder / TradingView)
├── signals/
│   ├── types.py          # Strategy TypedDicts
│   └── evaluator.py      # Strategy dict → boolean Series
├── backtest/
│   ├── engine.py         # Long-only simulation (next-bar open fills)
│   └── metrics.py        # Win rate, return, drawdown, equity PNG
├── tests/                # Unit tests (mirror package layout)
├── docker-compose.yml    # TimescaleDB on localhost:5433
└── docs/                 # HLD, roadmap, decisions, conventions
```

## Development

Install dev tools and run checks (required before commit per [docs/CONVENTIONS.md](docs/CONVENTIONS.md)):

```bash
pip install -r requirements-dev.txt
black .
ruff check . --fix
pytest
```

RSI tests use a committed fixture (`tests/fixtures/btc_usdt_1d_closes.csv`). Re-verify against
TradingView when refreshing that file (POC HLD step 3).

## Output

`run_poc.py` logs:

- Trade list (entry/exit dates, return %)
- Summary: trade count, win rate, total return, max drawdown, capital
- Entry signal dates (every bar where the condition was true)
- Path to `output/equity_curve.png`

## Documentation

| Doc | Contents |
|-----|----------|
| [docs/POC_HLD.md](docs/POC_HLD.md) | POC scope, stack, build order |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Full platform phases |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Architecture decision log |
| [docs/CONVENTIONS.md](docs/CONVENTIONS.md) | Code style and rules |

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `role "backtester" does not exist` on port 5432 | Local Postgres is bound to 5432; use Docker on **5433** (`docker compose up -d`) or set `DATABASE_URL` in `.env` |
| `No candles for ...` | DB empty or wrong symbol/range — delete rows or run fresh after `docker compose up` |
| Matplotlib cache warnings | Set `MPLCONFIGDIR=.matplotlib-cache` or ignore on first run |

## License

Not specified — add a license file if you open-source this repo.
