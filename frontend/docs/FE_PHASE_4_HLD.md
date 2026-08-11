# FE Phase 4 High Level Design — Watchlist + Symbol Search

**Status:** Implemented (v1)  
**Prerequisite:** [FE Phase 1](FE_PHASE_1_HLD.md)  
**Spec:** [SPEC-001 §4.3, §6.2, §7.1](SPEC-001.md)  
**Decisions:** D-85 (backend-primary workspace; interim IndexedDB cache), D-86 (symbol entities)  
**Roadmap:** [ROADMAP.md — Phase 4](ROADMAP.md#phase-4--watchlist--symbol-search)  
**Pipeline:** [docs/agents/fe-phase-4-watchlist/](../../docs/agents/fe-phase-4-watchlist/)

---

## Phase 4 Goal

Bootstrap a dev user, load/sync watchlists from the API, and let users switch chart symbols
from the sidebar. Symbol search uses backend structured entities everywhere.

---

## What Gets Built

| Area | Files |
|---|---|
| Bootstrap | `services/userBootstrap.ts` — `ensureUserId()`, `localStorage` key |
| API | `watchlistApi.ts` — nested list/create/`PUT …/symbols`; no append endpoint |
| Store | `stores/watchlistStore.ts` + IndexedDB via `idb-keyval` (`idbSet`/`idbGet`/`idbDel`) |
| UI | `WatchlistRoot`, `WatchlistPanel`, `WatchlistRow`; enhanced `SymbolSearch` |
| Integration | Row click → `chartStore.setSymbol(symbol)` |

**Backend endpoints (consumed as-is):**

```
POST /api/v1/users
GET  /api/v1/users?limit=&offset=
GET  /api/v1/users/{userId}
GET  /api/v1/users/{userId}/watchlists
POST /api/v1/users/{userId}/watchlists
PUT  /api/v1/users/{userId}/watchlists/{id}/symbols
GET  /api/v1/symbols/search?q=&active_only=
GET  /api/v1/symbols/{id}
```

---

## Architecture Notes

- **User bootstrap:** On app load, read `user_id` from `localStorage`; validate, create
  `Dev User` / `dev@local`, or recover `EMAIL_EXISTS` / stale `404` once.
- **Watchlist cache:** Hydrate from IndexedDB first for fast paint; successful API GET
  replaces cache wholesale (backend-primary).
- **Live prices:** Show `—` until Phase 11 live WS; do not poll or open a price WebSocket.
- **Symbol entities:** Rows and search hold full `Symbol` objects; API/chart IDs use `symbol.id`.

---

## Done Criteria

Phase 4 is **complete** when:

- [x] App creates or reuses a user on first load
- [x] Default watchlist loads from API into sidebar
- [x] Clicking a watchlist row switches active chart symbol
- [x] Symbol search adds symbol to watchlist
- [x] Watchlist survives page reload (IndexedDB cache)
- [x] All symbol references are `Symbol` objects, not raw strings

---

## References

- [SPEC-001.md](SPEC-001.md)
- [PHASE_4_HLD.md](../../backend/docs/PHASE_4_HLD.md) — users + watchlists
- [agent-h-report.md](../../docs/agents/fe-phase-4-watchlist/agent-h-report.md)
