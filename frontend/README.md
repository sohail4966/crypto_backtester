# Frontend

TradingView-style chart client for the crypto backtester platform.

## Docs

| Doc | Purpose |
|-----|---------|
| [SPEC-001](docs/SPEC-001.md) | Full architecture spec (v2.0) |
| [ROADMAP](docs/ROADMAP.md) | Implementation phases, status, backend gates |
| [FE_PHASE_*_HLD](docs/FE_PHASE_0_HLD.md) | Per-phase implementation guides |

## Status

Follow [ROADMAP](docs/ROADMAP.md) for phase-by-phase delivery.

| Phase | Scope | Status |
|-------|--------|--------|
| 0 | Vite scaffold, app shell, API client | ✅ |
| 1 | Core chart, windowed loading, symbol switching | ✅ |
| 2 | Overlay + subchart indicators from `/chart-data` | ✅ |
| 3 | WebSocket replay (`POST /replay/sessions`, WS tick batches) | ⬜ **current** |
| 4 | Watchlists, symbol entities, user bootstrap | ⬜ |
| 5 | MVP drawings (5 tools incl. Price Range) | ⬜ |
| 6 | Multi-chart layouts, sync, workspace, shortcuts | ⬜ |

**Backend ready for FE Phase 1–2:** [Phase 4b](../backend/docs/PHASE_4B_HLD.md) (`/chart-data`, symbol v2). **Replay:** [Phase 4c](../backend/docs/PHASE_4C_HLD.md) (WS streaming — in progress).

**Deferred:** live WS watchlist ticks (Phase 11), backtest HTTP API, workspace backend sync (Phase 4d).

## Quick start

```bash
# Terminal 1 — backend
cd backend && python -m api

# Terminal 2 — frontend
cd frontend && npm install && npm run dev
```

Open http://localhost:5173

## Keyboard shortcuts (Phase 6)

| Key | Action |
|-----|--------|
| `Space` | Replay play/pause |
| `→` | Step forward one bar |
| `Esc` | Cancel drawing tool |
| `Alt+1..4` | Layout 1×1 / 1×2 / 2×2 / 1+2 |
| `Ctrl+S` | Persist workspace to IndexedDB |
| `D/H/R/P/T` | Drawing tools |

## Backend

- [PHASE_4B_HLD.md](../backend/docs/PHASE_4B_HLD.md)
- [openapi.yaml](../backend/docs/openapi.yaml)

### Contract Notes

- Current chart and indicator UI uses `GET /chart-data`, `GET /indicators`, and `GET /symbols/{id}/data-range` without frontend-side indicator computation.
- No backend code change is required for the current frontend hardening pass.
- Future backend contract cleanup should document non-empty `signals` / `trades` payloads for Phase 4c and make derived timeframe data-range metadata consistent so the frontend no longer needs a `1m` fallback.
