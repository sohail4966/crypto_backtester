# FE Phase 6 High Level Design — Multi-Chart + Workspace Polish

**Status:** Not started  
**Prerequisite:** [FE Phases 1–5](FE_PHASE_1_HLD.md)  
**Spec:** [SPEC-001 §4.4, §6.2–6.3, §8](SPEC-001.md)  
**Decisions:** D-85 (workspace persistence), D-87 (multi-chart sync config)  
**Roadmap:** [ROADMAP.md — Phase 6](ROADMAP.md#phase-6--multi-chart--workspace-polish)

---

## Phase 6 Goal

Multi-pane chart layouts with configurable crosshair/range/symbol/timeframe sync, light/dark
theme toggle, workspace persistence, and keyboard shortcuts.

---

## What Gets Built

| Area | Files |
|---|---|
| Layout | `components/Layout/MultiChartLayout.tsx` — 1×1, 1×2, 2×2, 1+2 grids |
| Sync | `stores/syncStore.ts`, `hooks/useMultiChartSync.ts`, `SyncConfigPanel.tsx` |
| Workspace | `stores/workspaceStore.ts`, `services/workspaceStorage.ts` |
| Theme | Extend `ThemeProvider` — `data-theme` toggle, persist preference |
| Shortcuts | `hooks/useKeyboardShortcuts.ts` — global listener |
| Bootstrap | `app/AppBootstrap.tsx` — hydrate workspace + user on load |

**Sync categories (D-87):**

| Category | Default |
|---|---|
| `crosshair` | on |
| `visibleRange` | on |
| `symbol` | off |
| `timeframe` | off |

---

## Architecture Overview

```
workspaceStore
  ├── layouts[]     — pane configs (symbol, timeframe, indicators)
  ├── activeLayoutId
  └── theme

MultiChartLayout
  └── ChartContainer (paneId) × N
        └── useMultiChartSync(paneId) ──► syncStore publish/subscribe
```

**Persistence flow (interim — IndexedDB only):**

```
mutation → Zustand → debounced idbSet
startup  → idbGet → validate activeLayoutId → hydrate stores
Ctrl+S   → force persist
```

Phase 4d will add `GET/POST /workspace/sync` as authoritative store.

---

## Keyboard Shortcuts (SPEC-001 §8.3)

| Key | Action |
|---|---|
| `Space` | Replay play/pause |
| `→` | Step forward one bar |
| `Esc` | Cancel drawing tool |
| `Alt+1..4` | Layout presets |
| `Ctrl+S` | Persist workspace |
| `D/H/R/P/T` | Drawing tools |

---

## Architecture Notes

- **Per-pane chart instances:** Each `ChartContainer` owns one `IChartApi`; sync via
  `publishSync` / subscribe pattern — not shared chart ref.
- **Hydration validation:** If `activeLayoutId` missing from `layouts`, fallback to `layouts[0]`.
- **idb-keyval naming:** Import as `idbSet`/`idbGet` to avoid shadowing Zustand `set`.

---

## Done Criteria

Phase 6 is **complete** when:

- [ ] Layout switcher renders 1×1, 1×2, 2×2, 1+2 without crash
- [ ] Each pane can show independent symbol/timeframe
- [ ] Crosshair + visible-range sync toggles work across panes
- [ ] Symbol/timeframe sync toggles work when enabled
- [ ] Light/dark theme toggle persists across reload
- [ ] `Ctrl+S` saves workspace; reload restores layout + theme
- [ ] All keyboard shortcuts from SPEC-001 §8.3 work
- [ ] `npm run build` passes; full manual smoke across routes

---

## References

- [SPEC-001.md](SPEC-001.md)
- [ROADMAP.md](ROADMAP.md)
- Backend Phase 4d (workspace API — future)
