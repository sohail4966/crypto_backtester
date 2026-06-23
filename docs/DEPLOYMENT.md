# Deployment Guide

**Free stack:** Vercel frontend + Render free API + [Tiger Cloud](https://www.tigerdata.com/) free TimescaleDB.

```
Browser → Vercel (React) → Render API (FastAPI) → Tiger Cloud (TimescaleDB)
```

| Piece | Platform | Cost |
|-------|----------|------|
| Frontend | Vercel Hobby | $0 |
| API | Render free web service | $0 |
| Database | Tiger Cloud free service | $0 |

## Prerequisites

- GitHub repo pushed
- Accounts on [Vercel](https://vercel.com), [Render](https://render.com), [Tiger Data](https://www.tigerdata.com/)
- Tiger Cloud service created — copy the **connection string** from the dashboard

---

## 1. Tiger Cloud database

1. Create a **Free** service at [console.cloud.timescale.com](https://console.cloud.timescale.com/).
2. Copy the connection string:
   ```
   postgres://USER:PASSWORD@HOST:PORT/tsdb?sslmode=require
   ```
3. **IP allow list:** Render free tier uses dynamic outbound IPs. In Tiger Cloud → your service → **Settings → Allowed IP addresses**:
   - Allow `0.0.0.0/0` for a hobby demo, or
   - Disable the allow list if available.

   Without this, the Render API cannot reach the database.

4. Never commit the connection string to git.

---

## 2. Render API — manual setup

### Create the web service

1. [Render Dashboard](https://dashboard.render.com) → **New +** → **Web Service**.
2. Connect your GitHub repo (`crypto_backtester`).
3. Fill in the form:

   | Field | Value |
   |-------|-------|
   | **Name** | `crypto-backtester-api` (or any name) |
   | **Region** | Same region as Tiger Cloud if possible (e.g. `Oregon`) |
   | **Branch** | `main` (or your default branch) |
   | **Root Directory** | `backend` |
   | **Runtime** | **Docker** |
   | **Instance Type** | **Free** |

4. Under **Advanced** (expand if collapsed):

   | Field | Value |
   |-------|-------|
   | **Dockerfile Path** | `./Dockerfile` (relative to `backend/`) |
   | **Health Check Path** | `/api/v1/meta/health` |

   Leave **Docker Command** empty — the Dockerfile `CMD` starts uvicorn.

### Environment variables

Still on the create screen (or **Environment** tab after create):

| Key | Value |
|-----|-------|
| `DATABASE_URL` | Your Tiger Cloud string. `postgresql://` or `postgres://` both work. Keep `?sslmode=require`. |
| `CORS_ORIGINS` | Placeholder for now, e.g. `https://placeholder.vercel.app` — update after Vercel deploy |

Render injects `PORT` automatically; do not set it manually.

### Deploy

1. Click **Create Web Service**.
2. Wait for the Docker build and deploy to finish (first build ~3–5 min).
3. Copy the public URL, e.g. `https://crypto-backtester-api.onrender.com`.

On first start, the API runs DB migrations (`V001`–`V006`) against Tiger Cloud.

### Seed candle data (from your laptop)

Render **free** tier has no Shell, so backfill from your machine:

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export DATABASE_URL="postgresql://USER:PASSWORD@HOST:PORT/tsdb?sslmode=require"
python run_sync.py --backfill
```

Free Tiger storage is ~750 MB — keep `data.yaml` symbols/timeframes modest.

### Verify API

```bash
curl https://YOUR-API.onrender.com/api/v1/meta/health
curl "https://YOUR-API.onrender.com/api/v1/chart-data?symbol=BTC/USDT&timeframe=1h&limit=10"
```

First request after idle may take ~30–60s (Render free cold start).

---

## 3. Vercel frontend — manual setup

1. [Vercel Dashboard](https://vercel.com) → **Add New → Project**.
2. Import the same GitHub repo.
3. Configure:

   | Field | Value |
   |-------|-------|
   | **Root Directory** | `frontend` |
   | **Framework Preset** | Vite (auto-detected) |
   | **Build Command** | `npm run build` |
   | **Output Directory** | `dist` |

4. **Environment Variables:**

   | Key | Value |
   |-----|-------|
   | `VITE_API_BASE` | `https://YOUR-API.onrender.com/api/v1` |

5. Click **Deploy**.

### Update CORS on Render

After Vercel gives you a URL (e.g. `https://crypto-backtester.vercel.app`):

1. Render → your API service → **Environment**.
2. Set `CORS_ORIGINS` to that exact URL (no trailing slash).
3. Save — Render redeploys automatically.

---

## 4. Local development (unchanged)

```bash
# Terminal 1 — local DB
cd backend && docker compose up -d && python -m api

# Terminal 2 — frontend
cd frontend && npm run dev
```

Or point local API at Tiger Cloud:

```bash
export DATABASE_URL="postgresql://..."
python -m api
```

---

## Environment reference

### Backend (Render)

| Variable | Required | Purpose |
|----------|----------|---------|
| `DATABASE_URL` | Yes | Tiger Cloud connection string with `sslmode=require` |
| `CORS_ORIGINS` | Yes | Vercel URL |
| `PORT` | Auto | Set by Render |

### Frontend (Vercel)

| Variable | Required | Purpose |
|----------|----------|---------|
| `VITE_API_BASE` | Yes | `https://YOUR-API.onrender.com/api/v1` |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Docker build fails on TA-Lib | Check build logs; the Dockerfile uses Linux wheels — retry deploy |
| API health fails / DB error | Verify `DATABASE_URL`; Tiger IP allow list must allow Render |
| `create_hypertable` error | Use Tiger Cloud, not Render managed Postgres |
| CORS errors | `CORS_ORIGINS` must match Vercel URL exactly |
| Empty chart | Run `run_sync.py --backfill` locally with `DATABASE_URL` |
| 502 / slow first load | Render free cold start — wait ~60s and retry |
| Storage full on Tiger free | Reduce symbols in `data.yaml` |

## Security

- Never commit `DATABASE_URL` or paste credentials in chat/issues.
- Rotate the password in Tiger Cloud if it was ever exposed.
