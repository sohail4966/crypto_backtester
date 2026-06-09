# Frontend

TradingView-style chart client for the crypto backtester platform.

## Spec

**[SPEC-001 — TradingView-Style Frontend](docs/SPEC-001.md)** (v2.0)

## Status

All six SPEC-001 delivery phases are implemented against **Phase 4b** backend APIs.

| Phase | Scope | Status |
|-------|--------|--------|
| 1 | Core chart, windowed loading, symbol switching | ✅ |
| 2 | Overlay + subchart indicators from unified `/chart-data` | ✅ |
| 3 | Watchlists, symbol entities, user bootstrap, IndexedDB cache | ✅ |
| 4 | Hybrid REST replay (`POST /replay/runs`, chunk polling) | ✅ |
| 5 | MVP drawings (5 tools incl. Price Range), IndexedDB | ✅ |
| 6 | Multi-chart layouts, sync config, workspace persistence, shortcuts | ✅ |

**Deferred (backend):** live WS watchlist ticks (Phase 11), backtest HTTP API (Phase 4c), workspace backend sync (Phase 4d).

## Quick start

```bash
# Terminal 1 — backend
cd backend && python -m api

# Terminal 2 — frontend
cd frontend && npm install && npm run dev
```

Open http://localhost:5173

## Keyboard shortcuts

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
