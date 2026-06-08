# Crypto Backtester

A Python platform for crypto strategy research: sync OHLCV from exchanges, compute
indicators, evaluate YAML-defined strategies, and run a realistic backtest engine with
fees, sizing, risk exits, and performance analytics.

**Current status:** Phases 0–3 complete (data → indicators → full backtest engine).
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

### Database migrations

On every `run_backtest.py` startup, pending migrations in `data/migrations/sql/` are applied
automatically:

| File | Purpose |
|------|---------|
| `V001__schema_migrations.sql` | History table |
| `V002__create_candles_table.sql` | OHLCV table |
| `V003__create_candles_hypertable.sql` | Timescale hypertable |

Add `V004__your_change.sql` for schema changes — never edit applied migration files.

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

```bash
docker compose up -d
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # optional

python run_sync.py --backfill   # once, before first backtest
python run_backtest.py
```

Writes `output/equity_curve.png` and `output/trades.csv` (when `export_trades: true`).

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
├── config.yaml
├── run_backtest.py       # Backtest CLI
├── run_sync.py           # Data sync CLI
├── data/                 # fetch, store, get_candles()
├── indicators/           # 58-key registry + custom modules
├── signals/              # evaluator (AND, compare, dual, entry_trigger)
├── backtest/
│   ├── engine.py         # Bar loop (D-14)
│   ├── fills.py          # Slippage + commission
│   ├── risk.py           # Stops, TP, trailing
│   ├── sizing.py         # Position sizing
│   ├── metrics.py        # Return, Sharpe, Sortino, …
│   ├── benchmark.py      # Buy-and-hold return
│   └── export.py         # Trades CSV
└── docs/                 # HLD, ROADMAP, DECISIONS
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
