# PRD — FE Phase 4: Watchlist + Symbol Search

| Field | Value |
|---|---|
| **Status** | Approved (auto — no human in loop; defaults resolved in §9) |
| **Phase** | Frontend Phase 4 |
| **Product intent** | [FE_PHASE_4_HLD.md](../../../frontend/docs/FE_PHASE_4_HLD.md) |
| **Architecture** | [SPEC-001](../../../frontend/docs/SPEC-001.md) — symbol entities, persistence, symbol switching |
| **Backend** | ✅ [Backend Phase 4](../../../backend/docs/PHASE_4_HLD.md) — users and watchlists complete |
| **Decisions** | D-69 (no auth), D-85 (backend-primary persistence), D-86 (structured symbols) |

---

## 1. Problem / Goal

### Problem

The chart has a debounced symbol search in the topbar, but symbols cannot be saved for repeated use. The sidebar contains navigation and settings only, so users must search again whenever they want to revisit a market. There is also no frontend user bootstrap or persisted watchlist state despite the completed backend APIs.

### Goal

Deliver a persistent, user-scoped watchlist in the existing sidebar and enhance symbol search so a local analyst can:

1. Open the app and automatically create or reuse a development user.
2. See the default watchlist quickly from local cache, then synchronize it with the API.
3. Click a watchlist row to switch the active chart symbol.
4. Search the backend symbol catalog and add a structured `Symbol` entity to the selected watchlist.
5. Reload the app without losing the watchlist.

Success means commonly used markets are one click away, while `Symbol.id` remains the identifier used by chart and watchlist API calls.

---

## 2. User Roles

| Role | Need | Identity model |
|---|---|---|
| **Analyst / trader** | Save markets, switch the chart quickly, and add symbols from search. | Automatically bootstrapped development user stored in the browser. No login. |
| **Developer / QA** | Verify first-run bootstrap, cache hydration, API reconciliation, error handling, and symbol switching. | Same public API and browser-local user ID. |

Authentication, account selection, authorization, and user administration are deferred to Phase 11.

---

## 3. Scope

### In scope

- `ensureUserId()` bootstrap on application startup:
  - reuse the `user_id` held in `localStorage`;
  - otherwise create the fixed development user;
  - recover from a stale ID or duplicate development email.
- Load all watchlists for the bootstrapped user and select the backend default list.
- If the user has no watchlists, create a list named **Default**.
- IndexedDB cache for fast initial watchlist paint and reload resilience.
- Backend-primary reconciliation: cached data may paint first; a successful API response replaces it.
- Sidebar `WatchlistPanel` with:
  - selected-list control;
  - basic create-list action;
  - ordered symbol rows;
  - empty, loading, stale-cache, and error states.
- `WatchlistRow` showing ticker, exchange, and a price placeholder (`—`).
- Row click calls `chartStore.setSymbol(symbol)` with the complete `Symbol` object.
- Enhanced topbar `SymbolSearch`:
  - 250 ms debounced backend search;
  - ticker, exchange, and market type in results;
  - primary result selection switches the chart;
  - explicit add action adds the symbol to the selected watchlist without switching the chart;
  - duplicate add prevention and clear feedback.
- Watchlist mutation through the canonical backend operation:
  - `PUT /api/v1/users/{user_id}/watchlists/{watchlist_id}/symbols` with the complete ordered symbol-ID list.
- Tests for bootstrap, reconciliation, symbol search, add, duplicate prevention, and row-to-chart integration.
- Structured symbol entities throughout frontend state; no new raw-ticker state.

### Out of scope

- Rename, delete, reorder, drag-and-drop, import, or share watchlists.
- Removing a symbol from a watchlist.
- Live price, price-change, or volume updates.
- Authentication, login, account switching, and access control.
- Offline mutation queue or multi-device conflict resolution.
- Mobile-specific sidebar design.
- Backend changes.

### Current product baseline

- `SymbolSearch` already performs a 250 ms debounced query and switches `chartStore.symbol`.
- Search currently displays ticker and exchange only and has no add-to-watchlist action.
- `AppShell` has a collapsible 208 px sidebar.
- The sidebar currently contains Chart/Backtest navigation plus timezone and chart settings; no watchlist UI exists.
- The chart store already holds a complete `Symbol` entity.

---

## 4. UX Flows

### 4.1 First launch

```text
App starts
  → no local user_id
  → POST /api/v1/users { name: "Dev User", email: "dev@local" }
  → persist returned ID in localStorage
  → hydrate any watchlist cache for that ID
  → GET /api/v1/users/{id}/watchlists
  → select is_default list (or first ordered list)
  → render rows in sidebar and cache canonical response
```

The backend normally creates **Default** with all active symbols. If no list is returned, the frontend creates an empty **Default** list and selects it.

### 4.2 Returning launch

1. Read `user_id` from `localStorage`.
2. Hydrate that user's IndexedDB watchlist cache immediately.
3. Fetch watchlists from the API in the background.
4. Replace cached state with the successful backend response.
5. If the user no longer exists, clear the stale ID/cache, bootstrap once, and retry.
6. If refresh fails, keep cached rows visible with a non-blocking stale/offline message.

### 4.3 Switch symbol from watchlist

1. User clicks a watchlist row.
2. The complete row `Symbol` is passed to `chartStore.setSymbol`.
3. The selected row receives active styling.
4. Existing chart behavior refetches candles and indicators for `symbol.id`.
5. Sidebar remains open and selected watchlist remains unchanged.

### 4.4 Search and switch chart

1. User focuses the existing topbar search and types.
2. Search waits 250 ms, then calls `GET /api/v1/symbols/search?q=...`.
3. Results show ticker, exchange, and type; inactive symbols are excluded.
4. Clicking the result body switches the chart and closes the menu.
5. Empty query shows the backend's active catalog; no-results and request-error states are explicit.

### 4.5 Add a searched symbol

1. User opens search while a watchlist is selected.
2. User clicks the result's **Add** control.
3. If already present, no request is made and the row indicates **Added**.
4. Otherwise, the frontend optimistically appends the symbol and sends the full ordered ID list with `PUT .../symbols`.
5. On success, state is written to IndexedDB and the result indicates **Added**.
6. On failure, the optimistic change rolls back and an error message/toast is shown.
7. Adding does not switch the active chart and does not close the results menu.

### 4.6 Create and select another watchlist

1. User chooses **New watchlist** from the list selector.
2. A compact prompt accepts a trimmed name.
3. Empty names are rejected; valid names call `POST .../watchlists` with an empty symbol list.
4. The new list becomes selected and is cached after success.
5. Failure leaves the previous selection active and shows an error.

---

## 5. UI Surfaces

| Surface | Product behavior |
|---|---|
| **Sidebar / WatchlistPanel** | Occupies the flexible middle region below navigation and above settings. Includes “Watchlist” heading, list selector, new-list action, state messaging, and scrollable rows. |
| **Watchlist selector** | Defaults to `is_default`; otherwise lowest `sort_order`, then first response item. Supports selecting existing lists and creating a new one. |
| **WatchlistRow** | Shows ticker as primary text, exchange as secondary text, `—` in the price column, and active-chart styling. Entire row is keyboard-focusable and clickable. |
| **Topbar SymbolSearch** | Keeps current placement. Results display ticker, exchange, type, and an Add/Added control. Result body switches chart; Add has a separate action. |
| **Status feedback** | Inline loading/empty/stale/error states in the panel; existing toast mechanism for failed mutations. No blocking modal for network failures. |
| **Collapsed sidebar** | Existing collapse behavior is unchanged; watchlist is hidden with the sidebar and restored without losing selection. |

Accessibility requirements:

- Search remains labelled **Search symbols** and exposes loading/no-results status to assistive technology.
- Watchlist rows and search actions are reachable by keyboard with visible focus styles.
- Add action has a symbol-specific accessible name, e.g. **Add BTC/USDT to Default**.
- Active chart row uses both styling and `aria-current` or equivalent semantics.

---

## 6. Acceptance Criteria

1. **AC-1 — Bootstrap:** With no stored ID, app startup creates `Dev User`, stores the returned UUID, and does not create another user on the next reload.
2. **AC-2 — Bootstrap recovery:** A duplicate development email is resolved by reusing the matching backend user; a stale stored UUID is cleared and bootstrap retries at most once.
3. **AC-3 — Cache-first load:** Cached watchlists can render before the network response; a successful API response becomes canonical and updates IndexedDB.
4. **AC-4 — Default selection:** The list marked `is_default` is selected; deterministic fallback is lowest `sort_order`, then first item.
5. **AC-5 — Empty account:** If the API returns no lists, an empty **Default** watchlist is created and selected.
6. **AC-6 — Sidebar:** The expanded sidebar contains a usable watchlist panel without removing Chart/Backtest navigation, timezone, settings, or collapse behavior.
7. **AC-7 — Row switching:** Clicking or keyboard-activating a row passes its complete `Symbol` object to `chartStore.setSymbol`; the active row is visibly and semantically identified.
8. **AC-8 — Search:** Search remains backend-driven and 250 ms debounced, displays structured entities, and provides loading, no-results, and error states.
9. **AC-9 — Search selection:** Clicking a result body switches the chart, updates the input to the chosen ticker, and closes results.
10. **AC-10 — Add:** Clicking Add appends the symbol to the selected list through `PUT .../symbols`, preserves order, does not switch the chart, and updates IndexedDB after success.
11. **AC-11 — Duplicate safety:** Symbols already in the selected list show **Added**; repeated add attempts create no duplicate state and no mutation request.
12. **AC-12 — Mutation failure:** A failed add rolls back the optimistic state and gives visible feedback while preserving the last confirmed cache.
13. **AC-13 — Multiple lists:** User can create an empty named list, select among returned lists, and add to the currently selected list.
14. **AC-14 — Prices:** Every watchlist row renders `—` for price; no live WebSocket or per-row polling is introduced.
15. **AC-15 — Symbol model:** Watchlist and search state hold full `Symbol` entities; API/chart identifiers come from `symbol.id`, not a constructed ticker.
16. **AC-16 — Quality:** Relevant component/store/service tests, `npm test`, and `npm run build` pass.

---

## 7. Non-Goals

- A production identity model or secure per-user ownership.
- Live watchlist ticks, percentage movement, spark lines, or alerts.
- Full watchlist management (rename, delete, reorder, remove symbol).
- Search ranking personalization, recent searches, favorites outside watchlists, or fuzzy search implemented in the browser.
- Automatic switching of chart symbol when a symbol is added.
- Background offline writes, conflict dialogs, or timestamp-based merge logic.
- Changes to chart windowing, indicators, replay, drawings, or multi-chart layouts.

---

## 8. Dependencies

| Dependency | Status | Use in this phase |
|---|---|---|
| FE Phase 1 core chart and `chartStore` | ✅ Complete | Accepts structured symbols and refetches on symbol change. |
| Backend users API | ✅ Complete | `POST /api/v1/users`, plus lookup/recovery through existing user endpoints. |
| Backend watchlists API | ✅ Complete | Nested CRUD and canonical `PUT .../{id}/symbols` replacement. |
| Backend symbol search / v2 symbol entities | ✅ Complete | Structured search results and stable IDs (D-86). |
| Zustand | ✅ Present | Watchlist domain state and selected-list state. |
| TanStack Query | ✅ Present | Search and server fetch/mutation orchestration. |
| `idb-keyval` | Required by frontend architecture | Cache under the backend-primary model; import helpers with non-conflicting aliases. |
| Existing sidebar/topbar | ✅ Present | Integration surfaces; no route changes. |
| Phase 11 auth/live WS | Not required | Explicitly deferred. |

The live backend contract and OpenAPI are authoritative where older SPEC examples show top-level watchlist routes. Frontend must use the implemented nested `/users/{user_id}/watchlists` paths.

---

## 9. Product Decisions (auto-resolved)

| # | Open question | Decision |
|---|---|---|
| 1 | Where does the watchlist live? | **Inside the existing left sidebar**, below navigation and above the bottom settings block. No new route or right rail. |
| 2 | What does clicking a search result do? | **Result body switches the chart; a separate Add control saves it.** Adding never changes chart context. |
| 3 | Which list receives an added symbol? | **The currently selected watchlist.** On boot this is the backend default list. |
| 4 | Are multiple lists supported? | **Yes, minimally:** select and create. Rename/delete/reorder are deferred. |
| 5 | How are symbols added with the implemented API? | Use **`PUT .../symbols` with the full ordered list**. There is no assumed append endpoint. |
| 6 | What appears in the price column? | **`—` only.** No polling fallback; live prices wait for Phase 11. |
| 7 | How is cached data reconciled? | **Cache paints first; successful backend GET replaces it wholesale.** Failed refresh preserves cache with stale status. |
| 8 | Are offline mutations queued? | **No.** Mutations are optimistic but roll back on failure; only confirmed server state is persisted as canonical cache. |
| 9 | What if the stored user no longer exists? | Clear the ID and its cache, bootstrap once, then retry. Never loop indefinitely. |
| 10 | What if `dev@local` already exists after local storage is cleared? | Recover by exact email lookup through the public users API and reuse that user. |
| 11 | What if no default list exists? | Select lowest `sort_order`, then first response item; if no lists exist, create **Default**. |
| 12 | Does focus on an empty search query fetch results? | **Yes.** Show the active backend catalog, suitable for the current small universe. |
| 13 | How are duplicate adds handled? | Disable/label the action **Added**, compare by `Symbol.id`, and make no network request. |
| 14 | Is removal required to make Add reversible? | **No for Phase 4.** Removal and broader list management are deliberately deferred. |

---

## 10. References

- [frontend/docs/ROADMAP.md](../../../frontend/docs/ROADMAP.md) — Phase 4 scope and done-when
- [frontend/docs/FE_PHASE_4_HLD.md](../../../frontend/docs/FE_PHASE_4_HLD.md) — implementation intent
- [frontend/docs/SPEC-001.md](../../../frontend/docs/SPEC-001.md) — structured symbols, persistence, and switching
- [backend/docs/PHASE_4_HLD.md](../../../backend/docs/PHASE_4_HLD.md) — completed users/watchlists backend
- [frontend/src/components/Watchlist/SymbolSearch.tsx](../../../frontend/src/components/Watchlist/SymbolSearch.tsx) — current search baseline
- [frontend/src/components/Layout/Sidebar.tsx](../../../frontend/src/components/Layout/Sidebar.tsx) — current sidebar baseline
