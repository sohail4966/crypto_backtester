# Agent E Report — FE Phase 4: Watchlist + Symbol Search (Frontend)

| Field | Value |
|---|---|
| **Verdict** | **Complete** — full frontend per tech design |
| **Date** | 2026-08-11 |
| **Inputs** | [tech-design.md](./tech-design.md), [prd.md](./prd.md), [answers.md](./answers.md) |
| **Quality gate** | `npm test` + `npm run build` in `frontend/` — **pass** |

---

## Summary

Implemented backend-primary watchlists: fixed dev-user bootstrap with stale/`EMAIL_EXISTS` recovery, IndexedDB cache-first hydration, catalog + fallback symbol resolution, Zustand domain state, sidebar panel (select/create/rows), and SymbolSearch Add/Added without chart switch. Backend left untouched (Agent D no-op).

---

## Files created

### Types / constants / utils
- `frontend/src/types/watchlist.ts`
- `frontend/src/constants/watchlist.ts`
- `frontend/src/utils/watchlistNormalize.ts`
- `frontend/src/utils/watchlistNormalize.test.ts`

### Services
- `frontend/src/services/userBootstrap.ts`
- `frontend/src/services/userBootstrap.test.ts`
- `frontend/src/services/watchlistApi.ts`
- `frontend/src/services/watchlistApi.test.ts`
- `frontend/src/services/watchlistCache.ts`
- `frontend/src/services/watchlistCache.test.ts`

### Stores
- `frontend/src/stores/watchlistStore.ts`
- `frontend/src/stores/watchlistStore.test.ts`

### UI
- `frontend/src/components/Watchlist/WatchlistRoot.tsx`
- `frontend/src/components/Watchlist/WatchlistPanel.tsx`
- `frontend/src/components/Watchlist/WatchlistPanel.test.tsx`
- `frontend/src/components/Watchlist/WatchlistRow.tsx`
- `frontend/src/components/Watchlist/SymbolSearch.tsx` (rewritten)
- `frontend/src/components/Watchlist/SymbolSearch.test.tsx`

---

## Files changed

- `frontend/package.json` / `package-lock.json` — `idb-keyval`; `fake-indexeddb` (dev)
- `frontend/src/components/Layout/AppShell.tsx` — mounts `WatchlistRoot`
- `frontend/src/components/Layout/Sidebar.tsx` — flexible `WatchlistPanel` between nav and settings
- `frontend/src/app/App.test.tsx` — user/watchlist fetch fixtures + bootstrap assertion
- `frontend/src/test/setup.ts` — `fake-indexeddb/auto`

---

## Behavior coverage

| Area | Status |
|---|---|
| `ensureUserId()` + Strict Mode in-flight dedupe | Done |
| Stale user 404 clear + one recovery | Done |
| `EMAIL_EXISTS` exact-email paginated recovery | Done |
| Cache-first paint → canonical replace | Done |
| Empty lists → create Default (no redundant GET) | Done |
| Symbol ID → full `Symbol` (catalog + ≤4 concurrent fallback) | Done |
| Sidebar select / create / row → `chartStore.setSymbol` | Done |
| Search debounce, type display, Add/Added, toast on failure | Done |
| Optimistic add + per-list serialization + rollback | Done |

---

## Quality gate

```text
npm test   → 29 files / 121 tests passed
npm run build → tsc -b && vite build succeeded
```

---

## Notes / nits

- Selection changes persist to IndexedDB when cache is non-stale so returning launches keep the last selected list (answers §1).
- Empty-focus search enables the catalog immediately via TanStack Query; typed queries remain 250 ms debounced.
- No backend changes. Rename/delete/remove/live prices remain deferred.
