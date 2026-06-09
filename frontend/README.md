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
| 1 | Core chart, windowed loading, symbol switching | ⬜ |
| 2 | Overlay + subchart indicators from `/chart-data` | ⬜ |
| 3 | Watchlists, symbol entities, user bootstrap | ⬜ |
| 4 | Hybrid REST replay (`POST /replay/runs`, chunks) | ⬜ |
| 5 | MVP drawings (5 tools incl. Price Range) | ⬜ |
| 6 | Multi-chart layouts, sync, workspace, shortcuts | ⬜ |

**Backend ready for FE Phase 1+:** [Phase 4b](../backend/docs/PHASE_4B_HLD.md) (`/chart-data`, symbol v2, replay chunks).

**Deferred:** live WS watchlist ticks (Phase 11), backtest HTTP API (Phase 4c), workspace backend sync (Phase 4d).

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
