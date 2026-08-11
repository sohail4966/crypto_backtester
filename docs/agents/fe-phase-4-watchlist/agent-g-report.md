# Agent G Report — FE Phase 4: Watchlist (Review + Fixes)

| Field | Value |
|---|---|
| **Verdict** | **approve-with-nits** |
| **Date** | 2026-08-11 |
| **Reviewed** | Agent E frontend watchlist implementation vs [tech-design.md](./tech-design.md), [prd.md](./prd.md), [answers.md](./answers.md) |
| **Quality gate** | `npm test` + `npm run build` in `frontend/` — **pass** after fixes |

---

## Findings (severity)

### Critical

None.

### Important

1. **Empty watchlists still required a catalog fetch** — `resolveWatchlistDtos` always called `searchSymbols('')`. Empty **Default** creation / empty named lists could fail if search was down even though no IDs needed resolving (AC-5 / create flow).

2. **Successful PUT + failed resolve rolled back UI** — `addSymbolToSelected` treated resolve failure like mutation failure and restored the pre-add snapshot after the server had already accepted the ordered ID list (AC-10 / AC-12).

3. **Stale banner said “refreshing…” after a failed refresh** — panel keyed only on `stale`, so a ready+stale+error state kept claiming an in-flight refresh (AC-3 / status feedback).

### Nits (not fixed / acceptable)

- No dedicated `WatchlistRoot` RTL suite for cache-first deferred GET / empty-Default create (covered indirectly via App bootstrap + store/normalize/unit paths).
- `beginRefresh` status ternary is redundant (both branches `'refreshing'`).
- Manual live-API smoke still not run in this stage.

---

## Fixes applied

| Fix | Files |
|---|---|
| Skip catalog/fallback when every DTO has `symbols: []` | `utils/watchlistNormalize.ts`, `utils/watchlistNormalize.test.ts` |
| After PUT success, keep local/DTO-ordered symbols if resolve fails; rollback only when PUT fails | `components/Watchlist/WatchlistRoot.tsx` |
| Create-list resolve fallback via `mapWatchlistDto` | `components/Watchlist/WatchlistRoot.tsx` |
| Show “refreshing…” stale banner only for `hydrating` / `refreshing` | `components/Watchlist/WatchlistPanel.tsx`, `WatchlistPanel.test.tsx` |

---

## Spec compliance re-check (post-fix)

| Area | Status |
|---|---|
| `ensureUserId` + Strict Mode dedupe + EMAIL_EXISTS / stale 404 | OK |
| Cache-first hydrate → canonical replace; failed refresh keeps rows | OK |
| Empty lists → create Default without redundant list GET | OK |
| Symbol ID → full `Symbol` (catalog + ≤4 concurrent fallback) | OK |
| Sidebar select / create / row → `chartStore.setSymbol` + `aria-current` | OK |
| Search debounce, type display, Add/Added, toast on failure | OK |
| Optimistic add + per-list serialization + rollback on PUT failure | OK |
| Empty resolve / post-PUT resolve resilience | **Fixed** |
| Stale banner copy vs status | **Fixed** |

---

## Remaining nits

See Findings → Nits above. None block merge for v1.

---

## Test / build results after fixes

```
npm test   → 29 files, 122 tests passed
npm run build → tsc -b && vite build succeeded
```

---

## Final verdict

**approve-with-nits** — Important correctness/UX gaps fixed; remaining items are coverage polish / live smoke.
