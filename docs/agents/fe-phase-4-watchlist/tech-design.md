# Technical Design — FE Phase 4: Watchlist + Symbol Search

| Field | Value |
|---|---|
| Status | Ready for implementation |
| Product requirements | `docs/agents/fe-phase-4-watchlist/prd.md` |
| Frontend intent | `frontend/docs/FE_PHASE_4_HLD.md` |
| Backend dependency | Backend Phase 4 users/watchlists — complete |
| Backend work (Agent D) | **No-op**; verify the existing contract and make no backend changes |
| Implementation order | Agent D contract verification, then Agent E frontend implementation |

## 1. Summary

Phase 4 adds a frontend-only, backend-primary watchlist domain. App startup bootstraps or reuses the fixed development user, hydrates that user's last confirmed watchlists from IndexedDB, and then replaces cached state with the canonical backend response. The existing sidebar gains watchlist selection, creation, and symbol rows; the existing topbar search gains explicit add-to-watchlist behavior.

The backend is consumed as implemented. No database migration, backend route, schema, repository, or service change is required. The important adapter boundary is that backend watchlists contain ordered symbol ID strings, while frontend state must contain complete `Symbol` entities. The frontend resolves IDs before committing a server response to the Zustand store or IndexedDB.

## 2. Architecture

### 2.1 Component and data flow

```text
AppShell
  └─ WatchlistRoot (startup orchestration; renders children immediately)
       ├─ ensureUserId()
       │    ├─ localStorage
       │    └─ users API
       ├─ watchlist cache (IndexedDB)
       ├─ watchlists API
       ├─ symbol catalog / get-symbol API
       └─ watchlistStore

Sidebar
  └─ WatchlistPanel
       ├─ WatchlistSelector / create action
       └─ WatchlistRow[] ── complete Symbol ──> chartStore.setSymbol

Topbar
  └─ SymbolSearch
       ├─ symbol search query ── result body ──> chartStore.setSymbol
       └─ Add action ──> optimistic store update ──> PUT complete ID list
```

`WatchlistRoot` belongs inside `QueryProvider` and `ToastProvider`, alongside the existing shell-level `ReplayRoot`. It must not block route rendering: cache and network status are represented in the watchlist panel while the rest of the app remains usable.

### 2.2 Ownership boundaries

- **TanStack Query** owns remote request lifecycle, request deduplication, and the debounced symbol-search query.
- **Zustand `watchlistStore`** owns rendered watchlists, selected-list ID, bootstrap/load status, stale-cache status, and mutation snapshots.
- **IndexedDB** stores only the last server-confirmed resolved watchlist snapshot for one user key. Optimistic state is never cached.
- **`chartStore`** remains the sole owner of the active chart `Symbol`; the watchlist does not duplicate active-chart state.
- **React component-local state** owns search input/open state and the compact create-watchlist prompt.

### 2.3 Domain and transport models

Keep the API DTO distinct from the frontend domain:

```ts
interface WatchlistDto {
  id: string
  user_id: string
  name: string
  is_default: boolean
  sort_order: number
  symbols: string[]
  created_at: string
}

interface Watchlist {
  id: string
  userId: string
  name: string
  isDefault: boolean
  sortOrder: number
  symbols: Symbol[]
  createdAt: string
}
```

The adapter maps snake_case metadata and resolves every `symbols[]` ID to the existing frontend `Symbol` shape. No component or store may reconstruct a symbol from a ticker or retain raw ticker-only state.

### 2.4 Symbol resolution

For each canonical watchlist response:

1. Fetch the active catalog through the existing empty `GET /symbols/search?active_only=true`.
2. Build a `Map<Symbol.id, Symbol>`.
3. Resolve each watchlist's IDs in response order.
4. Deduplicate unresolved IDs across all lists, then call the existing `GET /symbols/{symbol_id}` endpoint with at most four fallback requests in flight.
5. Reject the refresh if an ID still cannot be resolved. Preserve confirmed cached state and show stale/error feedback rather than silently dropping or fabricating a symbol.

The catalog request is shared/deduplicated through a stable query key. Resolution reconstructs each list in backend order after fallback requests settle.

### 2.5 User bootstrap

Use constants for `user_id`, `Dev User`, and `dev@local`. `ensureUserId()` follows this bounded flow:

1. Read the stored ID.
2. If present, validate it with `GET /users/{id}`.
3. On success, return it.
4. On `404`, delete that user's watchlist cache and localStorage ID, then enter creation/recovery once.
5. If no ID exists, `POST /users`.
6. On success, store and return the new ID.
7. If creation returns `422` with backend code `EMAIL_EXISTS`, page through `GET /users?limit=500&offset={offset}` until an exact `email === "dev@local"` match is found or a page contains fewer than 500 users. Store and return an exact match; if none exists, fail bootstrap visibly.
8. Propagate all other errors. Never recurse or retry bootstrap more than once.

React Strict Mode can run startup effects twice in development. `ensureUserId()` must use a module-level in-flight promise (cleared in `finally`) or equivalent query deduplication so one app mount cannot issue two user-creation requests.

### 2.6 Load and reconciliation

After obtaining the user ID:

1. Read `watchlists:${userId}:v1` from IndexedDB and render a valid cached snapshot immediately.
2. Mark cached data as refreshing, not canonical.
3. Fetch the user's watchlist DTOs.
4. If none are returned, create `{ name: "Default", symbols: [] }` and use the successful create response directly without another list GET.
5. Resolve symbol IDs into full entities.
6. Replace store state wholesale with the server result.
7. Preserve a cached or in-memory selected ID when it still exists for the same user. Otherwise select the `isDefault` list, then lowest `sortOrder`, then response order.
8. Persist the resolved canonical snapshot.

If refresh fails and cache exists, retain rows and set a non-blocking stale message. If no cache exists, expose an error/Retry state. A `404 USER_NOT_FOUND` from either stored-user validation or watchlist listing clears the localStorage ID and only that user's cache, bootstraps once, and reloads once. A second stale-user result is a hard error.

### 2.7 Mutations

**Add symbol**

- Compare by `Symbol.id`; duplicate adds return without changing state or making a request.
- Capture the target list ID and its confirmed snapshot, optimistically append the complete `Symbol`, and disable Add controls for that target list until its request settles.
- Send the full ordered ID array with `PUT .../symbols`.
- On success, resolve the response and replace the captured target list by ID, regardless of which list is currently selected. Persist the complete snapshot without changing the user's current selection.
- On failure, restore the captured list, leave the prior cache untouched, and show a toast.
- The Add control stops event propagation/default mouse handling so it neither selects the search result nor closes the menu.

Serialize Add mutations per watchlist. This prevents racing full-list replacements on one list while allowing independent lists to mutate concurrently.

**Create watchlist**

- Trim the name and reject an empty value locally.
- Send `{ name, symbols: [] }`.
- On success, append/normalize the returned list, select it, and persist the new confirmed snapshot.
- Duplicate names are allowed by the live backend and are not rejected in the frontend.
- On failure, keep the previous selection and entered name, leave the prompt open, and show a toast. Close the prompt only after success. No optimistic placeholder list is needed.

## 3. Persistence and Database

### 3.1 Server database

There are **no new tables, columns, indexes, constraints, or migrations**. Existing Backend Phase 4 persistence remains authoritative.

### 3.2 Browser persistence

Add `idb-keyval` as a frontend runtime dependency and alias imports as `idbGet`, `idbSet`, and `idbDel`.

```ts
interface WatchlistCacheV1 {
  version: 1
  userId: string
  selectedWatchlistId: string | null
  watchlists: Watchlist[]
  confirmedAt: string
}
```

- Key: `watchlists:${userId}:v1`
- localStorage key: `user_id`
- Validate cache version, user ID, watchlists, and every nested full `Symbol` atomically before hydration; delete/ignore the entire record if any required field is malformed. Never partially hydrate a record.
- Persist only resolved full `Symbol` entities and server-confirmed mutations.
- Backend success replaces cache wholesale; no merge, offline queue, or conflict timestamp logic is introduced.
- Confirmed cache has no age-based expiry in Phase 4. It remains usable with stale/refreshing status until a successful backend response replaces it.

## 4. Backend Consumption and API Contract

All paths below are relative to the existing `/api/v1` base and use `apiRequest`.

| Operation | Request | Success | Frontend handling |
|---|---|---|---|
| Create dev user | `POST /users`, `{ name: "Dev User", email: "dev@local" }` | `201 UserResponse` | Persist returned UUID |
| List users for duplicate recovery | `GET /users?limit=500&offset={offset}` | `200 UserResponse[]` | Page until exact email match or short page |
| Validate stored user | `GET /users/{userId}` | `200 UserResponse` | Reuse ID |
| List watchlists | `GET /users/{userId}/watchlists` | `200 WatchlistDto[]` | Resolve ordered symbol IDs |
| Create watchlist | `POST /users/{userId}/watchlists`, `{ name, symbols: [] }` | `201 WatchlistDto` | Select after success |
| Replace symbols | `PUT /users/{userId}/watchlists/{watchlistId}/symbols`, `{ symbols: string[] }` | `200 WatchlistDto` | Canonical full-list replacement |
| Search/catalog | `GET /symbols/search?active_only=true&q={query}`; omit `q` when empty | `200 Symbol[]` | Existing structured v2 entity |
| Resolve one symbol | `GET /symbols/{encodedSymbolId}` | `200 Symbol` | Fallback for catalog misses |

Expected errors:

- `404 USER_NOT_FOUND`: stored user is stale; clear that user's local state and retry bootstrap once.
- `422 EMAIL_EXISTS`: duplicate dev-user creation; recover through the public users list.
- Other `404`/`422` or transport failures: surface through panel state or toast as appropriate.

The users list has no email filter. Page in batches of its implemented maximum of 500 and match the exact email. A short page ends the scan; absence is a hard bootstrap error. Production identity is deferred.

### 4.1 Agent D decision

**Agent D is a no-op.** The implemented routers, schemas, services, and OpenAPI already provide user creation/list/get, nested watchlist list/create, canonical ordered symbol replacement, symbol catalog search, and single-symbol resolution. Agent D should only verify these contracts and record that no backend code or migration is needed. Agent E must consume the live nested routes and must not add a speculative append endpoint or request an expanded watchlist response.

## 5. Frontend Modules

### 5.1 Create

| File | Responsibility |
|---|---|
| `frontend/src/types/watchlist.ts` | `UserResponse`, `WatchlistDto`, `Watchlist`, cache and status types |
| `frontend/src/constants/watchlist.ts` | storage/cache keys, dev-user identity, cache version |
| `frontend/src/services/userBootstrap.ts` | user API functions and bounded `ensureUserId()` |
| `frontend/src/services/watchlistApi.ts` | list/create/replace API calls and DTO mapping entry points |
| `frontend/src/services/watchlistCache.ts` | typed `idb-keyval` read/write/delete and shape validation |
| `frontend/src/utils/watchlistNormalize.ts` | DTO-to-domain conversion, ordered symbol resolution, default selection |
| `frontend/src/stores/watchlistStore.ts` | domain state, selection, hydration/canonical replacement, optimistic snapshot/rollback |
| `frontend/src/components/Watchlist/WatchlistRoot.tsx` | startup, cache hydration, reconciliation, retry, mutation orchestration |
| `frontend/src/components/Watchlist/WatchlistPanel.tsx` | panel layout, selector/create control, loading/stale/error/empty states |
| `frontend/src/components/Watchlist/WatchlistRow.tsx` | accessible row, ticker/exchange/price placeholder, active state |

Tests should be colocated using the existing `*.test.ts` / `*.test.tsx` convention.

### 5.2 Modify

| File | Change |
|---|---|
| `frontend/package.json` and lockfile | Add `idb-keyval`; add test-only IndexedDB support only if jsdom needs it |
| `frontend/src/components/Layout/AppShell.tsx` | Mount `WatchlistRoot` at shell scope |
| `frontend/src/components/Layout/Sidebar.tsx` | Insert flexible, min-height-safe `WatchlistPanel` between navigation and bottom settings |
| `frontend/src/components/Watchlist/SymbolSearch.tsx` | Add type display, request states, separate Add/Added control, selected-list integration |
| `frontend/src/app/App.test.tsx` | Extend fetch fixtures for bootstrap/watchlists so shell tests remain deterministic |

Do not modify chart fetch logic: existing consumers react to `chartStore.setSymbol(Symbol)` and use `symbol.id`.

## 6. UI and Accessibility

- The sidebar panel uses the available flexible middle region with an internal scroll area; navigation, settings, timezone, width, and collapse behavior remain unchanged.
- A row is a native button (or equivalent keyboard-operable control) and invokes `setSymbol(row.symbol)`.
- Active-row comparison is `chartSymbol?.id === row.symbol.id`; expose `aria-current`.
- Each row displays ticker, exchange, and literal `—` for price. No polling or WebSocket is added.
- The selector labels the current list and exposes a compact New watchlist action.
- Search remains labelled `Search symbols`, remains 250 ms debounced, trims input before requesting, and treats whitespace-only input as empty by omitting `q`.
- Focusing an empty search enables the active-catalog query. Reopening may reuse fresh TanStack Query data; focus alone does not force a network request.
- Search announces loading/no-results/error state.
- Search results show ticker, exchange, and market type.
- Result body switches the chart and closes the menu. Add uses an accessible name such as `Add BTC/USDT to Default`, does not switch the chart, and remains open.
- Existing toast infrastructure reports mutation failures; load and stale states remain inline in the panel.

## 7. Testing Strategy

### 7.1 Unit tests

**`userBootstrap.test.ts`**

- reuses and validates a stored ID;
- creates and stores a user when absent;
- deduplicates concurrent calls under Strict Mode;
- clears a stale `404` ID/cache and retries once;
- recovers `422 EMAIL_EXISTS` by exact email from `GET /users`;
- paginates duplicate-email recovery and fails when no exact match exists;
- does not loop and propagates unrelated errors.

**`watchlistNormalize.test.ts`**

- preserves backend symbol order;
- maps snake_case DTO metadata;
- uses catalog entities and falls back to `getSymbol`;
- fails rather than dropping an unresolved ID;
- selects default, then lowest `sortOrder`, then response order.

**`watchlistCache.test.ts`**

- round-trips a v1 confirmed snapshot;
- scopes keys by user;
- rejects the whole record for malformed nested symbols, wrong-user data, and unsupported versions;
- retains old but valid confirmed snapshots without age expiry;
- deletes stale-user cache.

**`watchlistStore.test.ts`**

- hydrates cache and marks it stale/refreshing;
- canonical replacement replaces cached data wholesale;
- selection is preserved only when still valid;
- duplicate detection uses symbol ID;
- optimistic append preserves order;
- serializes mutations per target list while allowing independent lists;
- applies a settled response to its captured target without changing current selection;
- rollback restores the exact confirmed snapshot.

**`watchlistApi.test.ts`**

- verifies nested URL encoding, methods, and request bodies;
- verifies replace uses the complete ordered ID list;
- verifies create sends an empty symbols array.

### 7.2 Component/integration tests

**`WatchlistPanel.test.tsx` / `WatchlistRow.test.tsx`**

- renders loading, empty, stale-cache, hard-error, and Retry states;
- renders selector and creates/selects a trimmed valid list;
- row click and keyboard activation pass the complete `Symbol` to `chartStore.setSymbol`;
- active row semantics and `—` price are present.

**`SymbolSearch.test.tsx`**

- waits 250 ms before querying and requests empty-query catalog on focus;
- trims queries, treats whitespace as empty, and permits fresh catalog-cache reuse on reopen;
- renders ticker, exchange, type, loading, no-results, and error states;
- result-body selection switches chart and closes results;
- Add targets the selected watchlist without switching chart or closing results;
- existing symbol shows Added and makes no PUT;
- failed add rolls back and reports an error.

**App-shell integration**

- first startup creates a user and loads the default list;
- returning startup paints IndexedDB cache before a deferred GET resolves;
- successful GET replaces cache;
- no-list response creates Default;
- no-list creation uses the create response without a redundant list GET;
- stale user from validation or watchlist listing recovers once;
- collapsed/expanded sidebar retains selected-list state.

Use fake timers for debounce and deterministic deferred promises for cache-first ordering. Reset Zustand, localStorage, IndexedDB, QueryClient, and mocks between tests. If jsdom lacks usable IndexedDB, add `fake-indexeddb` as a dev dependency rather than mocking away cache behavior.

### 7.3 Verification commands

From `frontend/`:

```bash
npm test
npm run lint
npm run build
```

## 8. Implementation Order

### Agent D — backend verification (no-op)

1. Verify live router/OpenAPI paths and methods.
2. Verify `WatchlistResponse.symbols` is an ordered `string[]`.
3. Verify user creation provisions the default list, `EMAIL_EXISTS` is `422`, stale user is `404`, and symbol lookup/search exist.
4. Record **NO-OP**; do not change backend code, schemas, migrations, or tests.

### Agent E — frontend implementation

1. Add `idb-keyval` and establish transport/domain types and constants.
2. Test and implement cache helpers and DTO normalization/symbol resolution.
3. Test and implement user bootstrap with stale/duplicate recovery and in-flight deduplication.
4. Test and implement watchlist API functions and Zustand state transitions.
5. Test and implement `WatchlistRoot` cache-first reconciliation and empty-account fallback.
6. Test and implement panel, selector/create flow, and accessible rows.
7. Test and enhance `SymbolSearch` selection/add/duplicate/error behavior.
8. Integrate root and panel into `AppShell`/`Sidebar`.
9. Update app fixtures, run focused tests, then full test/lint/build verification.

## 9. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Watchlist API returns IDs, not full entities | Resolve through catalog plus single-symbol fallback before store/cache commit |
| Strict Mode creates duplicate dev users | Deduplicate bootstrap with one shared in-flight promise |
| Duplicate email recovery has no filtered endpoint | Use exact email match from bounded public list; keep this explicitly dev-only |
| Stale local user causes retry loop | Permit one clear/bootstrap/reload recovery only |
| Optimistic full-list PUTs race and lose additions | Serialize by captured target watchlist and send that list's current ordered IDs |
| Failed optimistic add pollutes persistence | Cache only after confirmed success; rollback exact snapshot |
| Cache schema drifts | Version and validate records; ignore/delete invalid cache |
| Inactive symbol is absent from active catalog | Resolve catalog misses through `GET /symbols/{id}` |
| Network refresh hides useful cached rows | Preserve cache with stale status; backend replaces only on success |
| Sidebar content overflows 208 px layout | Use `min-h-0`, flex growth, and an internal row scroller |
| Add click also selects chart result | Separate controls and stop Add mouse/click propagation |
| Existing tests receive new startup requests | Provide explicit user/watchlist fixtures and isolated storage reset |

## 10. Deferred Work

Authentication, user selection, watchlist rename/delete/reorder/remove, live prices, offline mutation queues, conflict resolution, mobile-specific layout, and backend changes remain outside Phase 4.
