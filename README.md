# Crypto Backtester

Monorepo for crypto strategy research: data sync, indicators, backtest engine, and chart API.

| Directory | Purpose |
|-----------|---------|
| [`backend/`](backend/) | Python platform — TimescaleDB, indicators, backtest, FastAPI |
| [`frontend/`](frontend/) | Chart client (Phase 5+) — not started |

## Quick start

All Python commands run from **`backend/`**:

```bash
cd backend
docker compose up -d
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # optional

python run_sync.py --backfill
python run_backtest.py
python -m api          # http://localhost:8000
```

See [backend/README.md](backend/README.md) for full documentation.
