# FE Phase 4 High Level Design — Watchlist + Symbol Search

**Status:** Not started  
**Prerequisite:** [FE Phase 1](FE_PHASE_1_HLD.md)  
**Spec:** [SPEC-001 §4.3, §6.2, §7.1](SPEC-001.md)  
**Decisions:** D-85 (backend-primary workspace; interim IndexedDB cache), D-86 (symbol entities)  
**Roadmap:** [ROADMAP.md — Phase 4](ROADMAP.md#phase-4--watchlist--symbol-search)

---

## Phase 4 Goal

Bootstrap a dev user, load/sync watchlists from the API, and let users switch chart symbols
from the sidebar. Symbol search uses backend structured entities everywhere.

---

## What Gets Built

| Area | Files |
|---|---|
| Bootstrap | `services/userBootstrap.ts` — `ensureUserId()`, `localStorage` key |
| API | `createUser`, `getWatchlists`, `createWatchlist`, `addSymbolToWatchlist` |
| Store | `stores/watchlistStore.ts` + IndexedDB via `idb-keyval` (import as `idbSet`/`idbGet`) |
| UI | `WatchlistPanel.tsx`, `WatchlistRow.tsx`; enhance `SymbolSearch.tsx` |
| Integration | Row click → `chartStore.setSymbol(symbol)` |

**Backend endpoints:**

```
POST /api/v1/users                    body: { name, email }
GET  /api/v1/users/{userId}/watchlists
POST /api/v1/users/{userId}/watchlists
GET  /api/v1/symbols/search?q=
```

---

## Architecture Notes

- **User bootstrap:** On app load, read `userId` from `localStorage`; if missing, `POST /users`
  with dev defaults (`name: "Dev User"`, `email: "dev@local"`).
- **Watchlist cache:** Hydrate from IndexedDB first for fast paint; fetch API and merge
  (backend wins on conflict when Phase 4d lands).
- **Live prices:** Show `—` or last bar close until Phase 11 live WS; do not block on ticks.
- **Symbol entities:** `WatchlistRow` displays `symbol.ticker`; API calls use `symbol.id`.

---

## Done Criteria

Phase 4 is **complete** when:

- [ ] App creates or reuses a user on first load
- [ ] Default watchlist loads from API into sidebar
- [ ] Clicking a watchlist row switches active chart symbol
- [ ] Symbol search adds symbol to watchlist
- [ ] Watchlist survives page reload (IndexedDB cache)
- [ ] All symbol references are `Symbol` objects, not raw strings

---

## References

- [SPEC-001.md](SPEC-001.md)
- [PHASE_4_HLD.md](../../backend/docs/PHASE_4_HLD.md) — users + watchlists
