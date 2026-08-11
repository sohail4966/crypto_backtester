# Answers — FE Phase 6: Multi-Chart + Workspace Polish

1. **IndexedDB only.** Agent D is a hard no-op. No Phase 4d workspace API stubs.
2. **Shared global `indicatorStore`.** Per-pane indicator configs deferred; pane model may omit indicators field.
3. **Replay only on the active pane** (single existing session). No multi-session replay.
4. **Drawings stay global**, filtered by `symbolId` + `timeframe`. Interaction/keyboard only on the active pane.
5. **Leave `chartLayoutStore` alone.** It owns indicator sub-pane heights; multi-chart layouts live in `workspaceStore`.
6. **Clone pane[0] (or active pane if present)** symbol/timeframe when expanding pane count; generate new pane ids.
7. **Keep `cb-theme` localStorage as boot hint**; after workspace hydrate, `workspaceStore.theme` is source of truth and ThemeProvider follows it (also write-through to localStorage).
8. **Topbar** on chart route — LayoutSwitcher + SyncConfigPanel beside timeframe / indicators cluster.
9. **Apply logical range as-is** when `visibleRange` sync is on, even across differing timeframes (MVP). Users can disable sync for multi-TF independence.
10. **Yes** — toast “Workspace saved” on Ctrl+S flush success.
11. **Yes** — with `sync.symbol` on, watchlist/SymbolSearch updates all panes; with it off, only the active pane.
12. **Out of scope** — fixed CSS grid fractions only.
13. **Yes** — if `activeLayoutId` missing/invalid, use `layouts[0]`; if `activePaneId` missing, use that layout’s `panes[0].id`.
14. **Eager load** all visible panes (max 4). Simpler; acceptable for MVP.
