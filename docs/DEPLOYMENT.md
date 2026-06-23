# Deployment Guide

Deploy the **frontend** on [Vercel](https://vercel.com) and the **backend + TimescaleDB** on [Render](https://render.com).

```
Browser → Vercel (static React) → Render API (FastAPI) → TimescaleDB (private service)
```

## Prerequisites

- GitHub repo pushed (`sohail4966/crypto_backtester`)
- Vercel and Render accounts
- This monorepo structure (`frontend/`, `backend/`)

## 1. Backend + database on Render

### Option A — Blueprint (recommended)

1. In Render: **New → Blueprint**.
2. Connect the GitHub repo.
3. Render reads [`render.yaml`](../render.yaml) and creates:
   - `timescaledb` — private TimescaleDB container (persistent disk)
   - `crypto-backtester-api` — FastAPI web service (Docker)
4. When prompted for **CORS_ORIGINS**, enter your Vercel URL (you can update this after Vercel deploy), e.g.:
   ```
   https://your-app.vercel.app
   ```
5. Wait for both services to deploy. Note the API public URL, e.g. `https://crypto-backtester-api.onrender.com`.

### Option B — Manual setup

**TimescaleDB (private service)**

1. **New → Private Service → Deploy an existing image**
2. Image: `timescale/timescaledb:latest-pg16`
3. Environment:
   - `POSTGRES_USER=backtester`
   - `POSTGRES_DB=backtester`
   - `POSTGRES_PASSWORD` — generate a strong password
4. Add a **persistent disk** mounted at `/var/lib/postgresql/data` (10 GB).

**API (web service)**

1. **New → Web Service** → connect repo.
2. **Root directory:** `backend`
3. **Runtime:** Docker (uses [`backend/Dockerfile`](../backend/Dockerfile))
4. **Health check path:** `/api/v1/meta/health`
5. Environment variables:

   | Key | Value |
   |-----|-------|
   | `POSTGRES_USER` | `backtester` |
   | `POSTGRES_DB` | `backtester` |
   | `POSTGRES_PORT` | `5432` |
   | `POSTGRES_HOST` | Internal hostname of the TimescaleDB service (Render **Connect → Internal**) |
   | `POSTGRES_PASSWORD` | Same as TimescaleDB service |
   | `CORS_ORIGINS` | Your Vercel URL, e.g. `https://your-app.vercel.app` |

Render sets `PORT` automatically; the API binds to it.

### Seed candle data

The chart needs OHLCV data. After the API is healthy, open a **Shell** on the API service:

```bash
python run_sync.py --backfill
```

This fetches historical candles from Binance (network access required). It can take several minutes.

Verify:

```bash
curl https://YOUR-API.onrender.com/api/v1/meta/health
curl "https://YOUR-API.onrender.com/api/v1/chart-data?symbol=BTC/USDT&timeframe=1h&limit=10"
```

## 2. Frontend on Vercel

1. In Vercel: **Add New → Project** → import the GitHub repo.
2. **Root directory:** `frontend`
3. Framework preset: **Vite** (auto-detected)
4. Build settings (defaults are fine):
   - Build command: `npm run build`
   - Output directory: `dist`
5. **Environment variables:**

   | Key | Value |
   |-----|-------|
   | `VITE_API_BASE` | `https://YOUR-API.onrender.com/api/v1` |

6. Deploy.

[`frontend/vercel.json`](../frontend/vercel.json) adds SPA rewrites so React Router routes work.

### Update CORS after Vercel deploy

Copy your final Vercel URL and set it on Render:

```
CORS_ORIGINS=https://your-app.vercel.app
```

Redeploy the API service if needed.

## 3. Local development (unchanged)

```bash
# Terminal 1
cd backend && docker compose up -d && python -m api

# Terminal 2
cd frontend && npm run dev
```

Locally the Vite proxy serves `/api` → `localhost:8000`; no `VITE_API_BASE` needed.

## Environment reference

### Backend

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | — | Full Postgres URL (overrides `POSTGRES_*` parts) |
| `POSTGRES_HOST` | `localhost` | DB host (Render internal hostname) |
| `POSTGRES_PORT` | `5433` | DB port (`5432` in Docker/Render) |
| `POSTGRES_USER` | `backtester` | DB user |
| `POSTGRES_PASSWORD` | `backtester` | DB password |
| `POSTGRES_DB` | `backtester` | Database name |
| `PORT` | `8000` | HTTP port (set by Render) |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Comma-separated allowed origins |

### Frontend

| Variable | Default | Purpose |
|----------|---------|---------|
| `VITE_API_BASE` | `/api/v1` | API base URL in production |

## Notes

- **TimescaleDB required:** Migration `V003` creates a hypertable. Standard Render Postgres does not include TimescaleDB — use the private TimescaleDB service or [Timescale Cloud](https://www.timescale.com/).
- **Free tier cold starts:** Render free/starter web services sleep after inactivity; first request may take ~30s.
- **TA-Lib:** The Docker image installs `TA-Lib` from PyPI wheels on Linux.
- **WebSocket replay:** When you add replay UI, point WebSockets directly at the Render API (`wss://YOUR-API.onrender.com/ws/replay/...`); Vercel cannot proxy WebSockets to Render.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| API health fails | Check TimescaleDB is running; verify `POSTGRES_HOST` / password |
| CORS errors in browser | Set `CORS_ORIGINS` to exact Vercel origin (no trailing slash) |
| Empty chart | Run `python run_sync.py --backfill` in API shell |
| `create_hypertable` migration error | DB is plain Postgres — switch to TimescaleDB image |
| 502 on first request | Render cold start — retry after ~30s |
