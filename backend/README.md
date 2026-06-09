# Crypto Backtester

A Python platform for crypto strategy research: sync OHLCV from exchanges, compute
indicators, evaluate YAML-defined strategies, and run a realistic backtest engine with
fees, sizing, risk exits, and performance analytics.

**Current status:** Phases 0–4 complete (data → indicators → backtest → client API).
See [docs/ROADMAP.md](docs/ROADMAP.md).

## What it does

```
Exchange (Binance via ccxt) → TimescaleDB → get_candles() → indicators → signals → backtest → output
```

- **Data boundary:** everything below the DB reads candles through `get_candles()` (D-06).
- **Indicators:** 58-key TA-Lib + custom registry (Phase 2).
- **Backtest engine (Phase 3):** long/short, slippage, commission, four sizing modes,
  fixed/ATR/trailing stops, extended metrics, buy-and-hold benchmark, trades CSV.
- **No look-ahead on signals:** entries and signal exits fill at the **next bar open** (D-14).
- **Client API (Phase 4):** FastAPI REST + replay WebSocket for charts (no auth; historical + replay only).

### Database migrations

On application startup (`run_backtest.py` or `python -m api`), pending migrations in
`data/migrations/sql/` are applied automatically:

| File | Purpose |
|------|---------|
| `V001__schema_migrations.sql` | History table |
| `V002__create_candles_table.sql` | OHLCV table |
| `V003__create_candles_hypertable.sql` | Timescale hypertable |
| `V004__data_gaps.sql` | Data gap tracking |
| `V005__app_schema.sql` | API symbols, users, watchlists |

Add `V006__your_change.sql` for schema changes — never edit applied migration files.

## Prerequisites

- Python **3.11+**
- [Docker](https://docs.docker.com/get-docker/) (for TimescaleDB)
- Network access for historical fetch (Binance via ccxt)
- **TA-Lib** (indicator engine)

### TA-Lib install

**macOS:** `pip install TA-Lib` usually installs a wheel with the native library bundled.

**Linux / Docker:**

```bash
sudo apt-get install -y ta-lib
pip install TA-Lib==0.6.8
```

Pin is `TA-Lib==0.6.8` in [requirements.txt](requirements.txt).

## Quick start

Run from this `backend/` directory:

```bash
cd backend
docker compose up -d
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # optional

python run_sync.py --backfill   # once, before first backtest
python run_backtest.py
```

Writes `output/equity_curve.png` and `output/trades.csv` (when `export_trades: true`).

### Client API (Phase 4)

```bash
cd backend
docker compose up -d
python run_sync.py --backfill   # ensure candle data exists
python -m api                   # or: uvicorn api.main:app --reload --port 8000
```

- OpenAPI docs: http://localhost:8000/docs
- Base path: `/api/v1`
- Public endpoints (no auth): symbols, historical candles, indicators, users, watchlists, replay
- Replay WebSocket: `/ws/replay/{session_id}`

**Postman:** Import [docs/postman/Crypto_Backtester_API.postman_collection.json](docs/postman/Crypto_Backtester_API.postman_collection.json)
(optional environment: [docs/postman/Local.postman_environment.json](docs/postman/Local.postman_environment.json)).

See [docs/PHASE_4_HLD.md](docs/PHASE_4_HLD.md) for the full API contract.

## Configuration

| Source | Purpose |
|--------|---------|
| [config.yaml](config.yaml) | Symbol, timeframe, years, `backtest` block, named strategies |
| [data.yaml](data.yaml) | Ingestion settings for sync (symbols, exchanges, schedule) |
| `.env` | Secrets (`DATABASE_URL`) — never commit |

### Backtest block (`config.yaml`)

```yaml
backtest:
  slippage_bps: 5
  commission:
    type: percent
    rate: 0.001
  sizing:
    mode: full_capital
  export_trades: true
  trades_csv: output/trades.csv

active_strategy: your_strategy
strategies:
  your_strategy:
    benchmark: symbol          # or none
    entry_trigger: edge        # edge | level (default edge — avoids intraday churn)
    long:
      entry: { ... }
      exit: { ... }
      stop_loss: { type: atr_trail, period: 14, multiplier: 2.0 }
      take_profit: { type: risk_reward, ratio: 2.5 }
      sizing: { mode: risk_pct, risk_pct: 0.02 }
```

**Sizing modes:** `full_capital`, `fixed_pct`, `fixed_notional`, `risk_pct` (requires stop).

**Stop types:** `atr`, `fixed`, `atr_trail`, `fixed_pct_trail`.

**Take profit:** `fixed`, `risk_reward`.

See [docs/PHASE_3_HLD.md](docs/PHASE_3_HLD.md) for full config shapes and invariants.

## Data sync

```bash
python run_sync.py --once
python run_sync.py --backfill
```

## Project layout

```
crypto-backtester/
├── backend/              # Python platform (this directory)
│   ├── config.yaml
│   ├── run_backtest.py   # Backtest CLI
│   ├── run_sync.py       # Data sync CLI
│   ├── api/              # FastAPI + replay WebSocket
│   ├── data/             # fetch, store, get_candles()
│   ├── indicators/       # 58-key registry + custom modules
│   ├── signals/          # evaluator (AND, compare, dual, entry_trigger)
│   ├── backtest/
│   └── docs/             # HLD, ROADMAP, DECISIONS
└── frontend/             # Chart client (Phase 5+)
```

## Development

```bash
pip install -r requirements-dev.txt
black .
ruff check . --fix
pytest
```

## Output

`run_backtest.py` logs:

- Trade list (side, dates, return %, exit reason)
- Summary: win rate, total return, max drawdown, Sharpe, Sortino, Calmar, profit factor
- Benchmark and alpha (when `benchmark: symbol`)
- Paths to `output/equity_curve.png` and `output/trades.csv`

## Documentation

| Doc | Contents |
|-----|----------|
| [docs/openapi.yaml](docs/openapi.yaml) | **API contract** — REST + WebSocket schemas (request/response bodies) |
| [docs/PHASE_4_HLD.md](docs/PHASE_4_HLD.md) | Client API — completion assessment 8.5/10 |
| [docs/PHASE_4B_FE_GAPS.md](docs/PHASE_4B_FE_GAPS.md) | Derived timeframe API gaps found during FE Phase 1 |
| [docs/openapi.yaml](docs/openapi.yaml) | Static REST + WS API reference |
| [docs/postman/](docs/postman/) | Postman collection for manual API testing |
| [docs/PHASE_3_HLD.md](docs/PHASE_3_HLD.md) | Backtest engine design + completion assessment |
| [docs/PHASE_2_HLD.md](docs/PHASE_2_HLD.md) | Indicator library |
| [docs/PHASE_1_HLD.md](docs/PHASE_1_HLD.md) | Data foundation |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Full platform phases |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Architecture decision log (D-37–D-52) |
| [docs/CONVENTIONS.md](docs/CONVENTIONS.md) | Code style |

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `role "backtester" does not exist` on 5432 | Use Docker on **5433** (`docker compose up -d`) |
| `No candles for ...` | Run `python run_sync.py --backfill` |
| Too many trades on 15m/1h | Use `entry_trigger: edge` (default) and/or higher timeframe |
| Matplotlib cache warnings | Set `MPLCONFIGDIR=.matplotlib-cache` |

## License

Not specified — add a license file if you open-source this repo.
