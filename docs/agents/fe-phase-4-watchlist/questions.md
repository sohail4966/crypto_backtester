# Clarifying Questions — FE Phase 4: Watchlist + Symbol Search

1. On a returning launch, should a valid cached `selectedWatchlistId` take precedence over selecting the backend `is_default` list after reconciliation, or must every startup reset selection to the default?
2. If the stored user ID validates successfully but listing watchlists returns `404 USER_NOT_FOUND`, should the same bounded stale-user recovery path run, and which local data must be cleared?
3. When `dev@local` is recovered after `EMAIL_EXISTS`, should the frontend scan only the first users page, paginate until found, or treat absence from the first maximum-sized page as a hard bootstrap error?
4. What exact request body should be used when creating the fallback **Default** watchlist after an empty list response, and should frontend initialization retry the list GET after creation or use the create response directly?
5. How should malformed or partially unresolved cached `Symbol` entities be handled: discard the entire cache record, drop only invalid symbols, or retain it until network refresh?
6. When resolving watchlist symbol IDs, should single-symbol fallback requests run sequentially, concurrently without a bound, or with bounded concurrency; and should one unresolved ID fail the whole canonical refresh?
7. Should symbol-search queries be trimmed before requesting, and should whitespace-only input behave exactly like the empty query by loading the active catalog?
8. If the search menu opens with an empty query and later reopens without input changes, may TanStack Query reuse cached catalog data, or must focus always force a network refetch?
9. While an Add mutation is pending, should adding be disabled globally, only for the selected watchlist, or only for the target symbol; and what happens if the user selects another watchlist before the request settles?
10. If an Add request succeeds after the selected watchlist changes, which list should receive the canonical response and which list should remain selected?
11. Are duplicate watchlist names allowed, and if the backend rejects one, should the compact create prompt stay open with inline feedback or close and rely on a toast?
12. Does the project already provide a toast API suitable for mutation failures, or should Phase 4 use inline errors if no toast infrastructure exists?
13. Should cached confirmed data have any age-based expiry, or remain usable indefinitely with stale status until a successful backend refresh replaces it?
14. Does the live backend contract fully support the documented no-op decision for Agent D, including ordered symbol replacement, default-list provisioning, duplicate-email recovery, and inactive single-symbol lookup?
