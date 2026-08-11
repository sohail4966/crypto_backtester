# Clarifying Questions — FE Phase 6: Multi-Chart + Workspace Polish

1. Is workspace persistence IndexedDB-only for this phase, or should Agent D stub Phase 4d `GET/POST /workspace`?
2. Should per-pane indicator configs ship now, or keep a shared global `indicatorStore`?
3. Does multi-pane replay mean N sessions, or replay only on the active pane?
4. Are drawings pane-scoped, or continue global filter by `symbolId` + `timeframe`?
5. Should `chartLayoutStore` (indicator sub-pane heights) be renamed/merged into workspace, or left alone?
6. On layout preset expand, how are new panes seeded (clone active pane vs defaults)?
7. Should ThemeProvider drop `localStorage` entirely, or keep it as a boot hint beside IndexedDB workspace?
8. Where should LayoutSwitcher and SyncConfigPanel live in chrome (topbar vs sidebar)?
9. For visible-range sync across different timeframes, sync logical range as-is, or skip when timeframes differ?
10. Should Ctrl+S show a toast on successful save?
11. When symbol sync is on and watchlist sets a symbol, do all panes update immediately?
12. Is drag-resize of multi-chart grid cells in scope?
13. If `activeLayoutId` is missing after hydrate, fallback to `layouts[0]`?
14. Should secondary (inactive) panes still load candle data, or lazy-load only when activated?
