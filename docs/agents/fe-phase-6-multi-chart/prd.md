# PRD — FE Phase 6: Multi-Chart + Workspace Polish

| Field | Value |
|---|---|
| **Status** | Approved (auto — no human in loop; defaults resolved in answers.md) |
| **Phase** | Frontend Phase 6 |
| **Product intent** | [FE_PHASE_6_HLD.md](../../../frontend/docs/FE_PHASE_6_HLD.md) |
| **Architecture** | [SPEC-001](../../../frontend/docs/SPEC-001.md) §4.4, §5.4 N/A, §8.2–8.3, §9 |
| **Backend** | None required — IndexedDB only (D-85 interim); Phase 4d workspace API deferred |
| **Decisions** | D-85 (IndexedDB until 4d), D-87 (sync categories) |

---

## 1. Problem / Goal

### Problem

Analysts are limited to a single chart pane. Multi-timeframe and multi-symbol monitoring requires opening separate windows. Theme and layout preferences are only partially persisted (`localStorage` theme), and there is no unified workspace snapshot or sync-config UI.

### Goal

Deliver multi-pane layouts with configurable sync, theme persistence via workspace, and IndexedDB workspace save/restore so a local analyst can:

1. Switch among 1×1, 1×2, 2×2, and 1+2 layouts (Alt+1..4).
2. Give each pane its own symbol and timeframe (defaults: symbol/tf sync off).
3. Sync crosshair and visible range across panes when enabled (defaults on).
4. Toggle sync categories in a SyncConfigPanel.
5. Persist theme + layout workspace to IndexedDB; force-save with Ctrl+S; restore on reload.
6. Keep replay, watchlist, and drawings working on the **active** pane without regressions.

Success means a 2×2 grid shows four independent charts, sync toggles work, and layout + theme survive reload from IndexedDB — no Phase 4d API required.

---

## 2. User Roles

| Role | Need | Identity model |
|---|---|---|
| **Analyst / trader** | Compare symbols/TFs side-by-side; keep workspace between sessions. | Same browser-local session as Phases 4–5; no login. |
| **Developer / QA** | Verify layouts, sync, persistence, non-regression of replay/watchlist/drawings. | Same public API + IndexedDB. |

---

## 3. Scope

### In scope

- Layout presets: `1x1`, `1x2`, `2x2`, `1plus2` (1+2 = one tall left + two stacked right).
- `MultiChartLayout` CSS grid rendering N independent `ChartContainer` instances.
- Per-pane `symbol` + `timeframe` in `workspaceStore` layouts.
- Active pane focus (click pane chrome); SymbolSearch / TimeframeSelector / watchlist row update the **active** pane (and `chartStore` mirror).
- `syncStore` + `useMultiChartSync` for D-87 categories: `crosshair`, `visibleRange`, `symbol`, `timeframe`.
- `SyncConfigPanel` UI (toggles for four categories).
- Layout switcher control in topbar (chart route).
- `workspaceStore` + `workspaceStorage` IndexedDB blob (`workspace:v1`).
- Theme owned by workspace (ThemeProvider reads/writes `workspaceStore.theme`); still apply `data-theme` on document.
- Debounced persist on mutation; Ctrl+S force persist (toast optional).
- Keyboard: Alt+1..4 layout presets; Ctrl+S save (plus existing replay/drawing shortcuts unchanged).
- `WorkspaceRoot` hydrate on boot; validate `activeLayoutId`.
- Tests for stores, storage, sync hook, layout switcher; `npm test` + `npm run build`.
- Update ROADMAP / FE_PHASE_6_HLD / PIPELINE_QUEUE status when done.

### Out of scope

- Backend `GET/POST /workspace` sync (Phase 4d).
- Per-pane independent indicator sets (global `indicatorStore` shared; pane may store optional future field but MVP shares indicators).
- Multi-pane simultaneous replay (replay remains single-session on active pane / chartStore only).
- Per-pane drawings isolation beyond existing symbol+tf filter (drawings still scoped by symbolId+timeframe globally).
- Drag-to-resize multi-chart grid cells (fixed CSS grid fractions).
- Mobile-specific multi-chart UX (SPEC-009).
- Changing `chartLayoutStore` (indicator sub-pane heights) semantics — leave as-is.

### Current product baseline

- Single `ChartContainer` on `ChartPage`; `paneId` prop already exists (default `'main'`).
- `chartStore` holds one symbol/timeframe; theme in ThemeProvider `localStorage` (`cb-theme`).
- `chartLayoutStore` = indicator sub-pane heights only (unrelated to multi-chart layouts).
- Replay / drawings / watchlist wired to chartStore + ChartContainer.
- IndexedDB patterns proven (`drawingCache`, `watchlistCache`).

---

## 4. UX Flows

### 4.1 Switch to 2×2

```text
User clicks Layout → 2×2 (or Alt+3)
  → workspaceStore.setLayoutPreset('2x2')
  → ensure 4 panes (clone symbol/tf from pane 0 for new panes)
  → MultiChartLayout renders 2×2 grid of ChartContainers
  → active pane retains focus styling
```

### 4.2 Independent symbol on pane B

```text
User clicks pane B → activePaneId = B; chartStore mirrors B's symbol/tf
User picks ETH from SymbolSearch
  → chartStore.setSymbol(ETH)
  → workspace writes ETH into pane B
  → if sync.symbol on → all panes get ETH; else only B
```

### 4.3 Crosshair sync

```text
User moves crosshair on pane A
  → publishSync({ type: 'crosshair', value: time, sourcePaneId })
  → panes with crosshair sync apply setCrosshairPosition (skip source)
```

### 4.4 Persist workspace

```text
Any layout/theme/sync/pane mutation → debounced idbSet(workspace:v1)
Ctrl+S → immediate persist + toast “Workspace saved”
Reload → hydrate layouts, theme, sync, active ids; ThemeProvider applies theme
```

---

## 5. Acceptance Criteria

| ID | Criterion |
|---|---|
| **AC-1** | Layout switcher exposes 1×1, 1×2, 2×2, 1+2 without crash |
| **AC-2** | Alt+1..4 switches the four presets when not in an editable field |
| **AC-3** | Each pane can show independent symbol and timeframe when symbol/tf sync are off |
| **AC-4** | Clicking a pane sets it active; topbar symbol/tf and watchlist update that pane |
| **AC-5** | Crosshair sync on/off works across panes |
| **AC-6** | Visible-range sync on/off works across panes |
| **AC-7** | Symbol and timeframe sync toggles propagate when enabled |
| **AC-8** | SyncConfigPanel exposes all four D-87 toggles with correct defaults |
| **AC-9** | Light/dark theme toggle persists across reload via workspace IndexedDB |
| **AC-10** | Ctrl+S saves workspace; reload restores layout preset, panes, sync, theme |
| **AC-11** | Corrupt/missing workspace blob → safe defaults; app does not crash |
| **AC-12** | Replay, watchlist, drawings continue to work on active pane (1×1 and multi) |
| **AC-13** | `npm test` and `npm run build` pass |

---

## 6. Non-Goals / Explicit Deferrals

- Server workspace authority (D-85 full path) → Phase 4d.
- Per-pane indicator configurations.
- Multi-replay sessions.

---

## 7. Dependencies

| Dependency | Status |
|---|---|
| FE Phases 1–5 | Complete (v1) |
| Phase 4d workspace API | Not required (interim IndexedDB) |
| D-87 sync categories | Locked |

---

## 8. Risks

| Risk | Mitigation |
|---|---|
| N chart instances × chunk managers = memory/CPU | Cap at 4 panes; destroy charts on layout shrink |
| Sync feedback loops | `sourcePaneId` + applying flag; ignore echo |
| Breaking replay/drawings | Gate interaction hooks to `isActive` pane only |
| Theme dual-write (localStorage vs IDB) | Workspace is SoT after hydrate; ThemeProvider syncs from workspaceStore |

---

## 9. Auto-approved defaults

See [answers.md](./answers.md). Highlights: IndexedDB-only; shared global indicators; replay/drawings on active pane only; `chartLayoutStore` untouched; Agent D no-op.
