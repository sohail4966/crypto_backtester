# Technical Design — FE Phase 6: Multi-Chart + Workspace Polish

| Field | Value |
|---|---|
| Status | Ready for implementation (post B2 answers) |
| Product requirements | `docs/agents/fe-phase-6-multi-chart/prd.md` |
| Frontend intent | `frontend/docs/FE_PHASE_6_HLD.md` |
| Backend dependency | None |
| Backend work (Agent D) | **No-op** — interim IndexedDB only; Phase 4d deferred |
| Implementation order | Agent D verification → Agent E frontend |

## 1. Summary

Phase 6 adds multi-pane chart layouts, D-87 sync categories, workspace persistence in IndexedDB, and theme ownership via `workspaceStore`. Each grid cell is an independent `ChartContainer` / `IChartApi`. `chartStore` remains the **active-pane mirror** so existing SymbolSearch, watchlist, replay, and drawings keep working. No backend routes.

**Naming note:** Existing `chartLayoutStore` manages **indicator sub-pane heights** only. Multi-chart layouts live in `workspaceStore`. Do not overload `chartLayoutStore`.

## 2. Architecture

### 2.1 Component and data flow

```text
App
  └─ ThemeProvider (reads/writes workspaceStore.theme after hydrate)
       └─ AppShell
            └─ WorkspaceRoot (hydrate IDB → workspace + sync; debounce persist; Ctrl+S; Alt+1..4)
                 └─ WatchlistRoot / ReplayRoot / DrawingsRoot (unchanged order)

ChartPage
  └─ MultiChartLayout
       ├─ LayoutSwitcher + SyncConfigPanel (or mounted in Topbar)
       └─ ChartContainer × N
            ├─ props: paneId, isActive, symbol, timeframe
            └─ useMultiChartSync(paneId) → publish/subscribe syncStore
```

### 2.2 Ownership boundaries

| Owner | Responsibility |
|---|---|
| `workspaceStore` | `layouts[]`, `activeLayoutId`, `activePaneId`, `theme`, layout/pane mutations |
| `syncStore` | Sync config (4 booleans) + ephemeral last crosshair/range + pub/sub |
| `workspaceStorage` | IndexedDB `workspace:v1` read/write/validate |
| `WorkspaceRoot` | Hydrate once; debounce persist; keyboard Alt+1..4 + Ctrl+S |
| `chartStore` | Active-pane mirror (symbol/tf); existing consumers unchanged |
| `chartLayoutStore` | **Unchanged** — indicator sub-pane heights |
| `ChartContainer` | Optional overrides; `isActive` gates drawings/replay interaction; sync hooks |
| ThemeProvider | Apply `data-theme`; prefer `workspaceStore.theme` when hydrated |

### 2.3 Domain model

```ts
type LayoutPreset = '1x1' | '1x2' | '2x2' | '1plus2'

interface WorkspacePane {
  id: string
  symbol: Symbol | null  // structured entity when known
  timeframe: ChartTimeframe
}

interface ChartLayout {
  id: string
  name: string
  preset: LayoutPreset
  panes: WorkspacePane[]
}

interface SyncConfig {
  crosshair: boolean      // default true
  visibleRange: boolean   // default true
  symbol: boolean         // default false
  timeframe: boolean      // default false
}

type SyncEvent =
  | { type: 'crosshair'; sourcePaneId: string; time: number | null }
  | { type: 'visibleRange'; sourcePaneId: string; range: { from: number; to: number } | null }
  | { type: 'symbol'; sourcePaneId: string; symbol: Symbol }
  | { type: 'timeframe'; sourcePaneId: string; timeframe: ChartTimeframe }
```

### 2.4 Pane counts per preset

| Preset | Panes | CSS |
|---|---|---|
| `1x1` | 1 | single cell |
| `1x2` | 2 | `grid-cols-2` |
| `2x2` | 4 | `grid-cols-2 grid-rows-2` |
| `1plus2` | 3 | left spans 2 rows; right two stacked |

When switching presets, **reuse existing pane ids** in order; append clones of pane[0] (or last) for new slots; drop extras (destroy charts via React unmount).

### 2.5 Active pane bridge

```text
setActivePane(paneId):
  activePaneId = paneId
  chartStore.symbol/timeframe ← pane's values (if symbol non-null)

chartStore.setSymbol(s) / setTimeframe(tf):
  update active pane in workspaceStore
  if sync.symbol / sync.timeframe → update all panes
  publish SyncEvent for subscribers (optional; direct store write is enough)
```

Watchlist / SymbolSearch / TimeframeSelector keep calling `chartStore` only — bridge lives in WorkspaceRoot (subscribe) or wrapped setters in chartStore middleware. Prefer **WorkspaceRoot effect** + **workspaceStore.updateActivePaneFromChart** called from thin wrappers, or patch chartStore setters to notify workspace. Cleanest MVP: extend `chartStore.setSymbol`/`setTimeframe` to call a registered bridge callback set by WorkspaceRoot (`setChartWorkspaceBridge`).

### 2.6 ChartContainer changes

New/extended props:

```ts
interface ChartContainerProps {
  paneId?: string          // default 'main'
  className?: string
  isActive?: boolean       // default true (1×1 / single)
  symbolOverride?: Symbol | null
  timeframeOverride?: ChartTimeframe
  onActivate?: () => void
}
```

- Data path: `symbol = symbolOverride ?? chartStore.symbol`, same for timeframe.
- `useDrawingKeyboard` / `useDrawingInteraction` / `useReplayChart` only when `isActive`.
- Click on container chrome calls `onActivate`.
- `useMultiChartSync`: subscribe crosshair + visibleLogicalRange; publish with `sourcePaneId`; apply with loop guard.

Secondary panes still run `useChunkManager` with their symbol/tf (independent data). Replay trail data only applies when `isActive` (trailAuthoritative + isActive).

### 2.7 Sync implementation

`syncStore`:

- `config: SyncConfig`
- `setSyncCategory(key, value)`
- `subscribe(listener): unsubscribe`
- `publish(event: SyncEvent)` — notifies listeners; publisher ignores own echo via `sourcePaneId`

`useMultiChartSync(paneId, chart, candleSeries, enabled)`:

- On crosshair move → if `config.crosshair` → publish
- On visible logical range change → if `config.visibleRange` → publish (debounce ~32ms optional)
- On event from other pane → apply to local chart if category enabled

Symbol/tf sync implemented in workspace/chart bridge (not chart API).

### 2.8 Persistence

```ts
// constants/workspace.ts
WORKSPACE_CACHE_VERSION = 1
WORKSPACE_CACHE_KEY = 'workspace:v1'
WORKSPACE_PERSIST_DEBOUNCE_MS = 400

interface WorkspaceCacheV1 {
  version: 1
  savedAt: string
  theme: Theme
  activeLayoutId: string
  activePaneId: string
  layouts: ChartLayout[]
  sync: SyncConfig
}
```

Validate on read; corrupt → delete key, use defaults. Defaults: one layout `default` preset `1x1`, one pane, theme from existing `cb-theme` localStorage or `'dark'`, sync D-87 defaults.

Ctrl+S: `preventDefault`, `flushWorkspacePersist()`, toast.

### 2.9 Theme

- After workspace hydrate: `workspaceStore.theme` is SoT; ThemeProvider subscribes and applies.
- Toggle updates `workspaceStore.setTheme` → document + persist via WorkspaceRoot debounce.
- Keep writing `cb-theme` localStorage as fast boot hint before IDB resolves (optional, recommended).

### 2.10 Keyboard

`useWorkspaceKeyboard` in WorkspaceRoot:

- Skip `isEditableTarget`
- `Alt+1`..`Alt+4` → presets
- `Ctrl+S` / `Meta+S` → flush persist
- Do not steal Space / arrows / drawing keys

### 2.11 Files to add/touch

| Path | Action |
|---|---|
| `types/workspace.ts` | add |
| `constants/workspace.ts` | add |
| `stores/workspaceStore.ts` | add |
| `stores/syncStore.ts` | add |
| `services/workspaceStorage.ts` | add |
| `hooks/useMultiChartSync.ts` | add |
| `hooks/useWorkspaceKeyboard.ts` | add |
| `components/Layout/MultiChartLayout.tsx` | add |
| `components/Layout/LayoutSwitcher.tsx` | add |
| `components/Layout/SyncConfigPanel.tsx` | add |
| `components/Workspace/WorkspaceRoot.tsx` | add |
| `pages/ChartPage.tsx` | use MultiChartLayout |
| `components/Chart/ChartContainer.tsx` | overrides + sync + isActive |
| `components/Layout/Topbar.tsx` | LayoutSwitcher + SyncConfigPanel |
| `components/Layout/AppShell.tsx` | wrap WorkspaceRoot |
| `app/ThemeProvider.tsx` | sync with workspaceStore |
| `stores/chartStore.ts` | optional bridge hook for pane write-back |
| Tests for store/storage/sync/layout | add |

## 3. Testing strategy

- Unit: workspaceStorage validate/round-trip; workspaceStore preset transitions; syncStore publish/subscribe; defaults.
- Component: LayoutSwitcher changes preset; SyncConfigPanel toggles.
- Hook: useMultiChartSync applies range/crosshair with source skip (mock chart).
- Regression: existing App / ChartContainer / Replay / Watchlist / Drawings tests stay green.
- Gate: `npm test`, `npm run build`.

## 4. Agent D

Hard no-op. No OpenAPI / migration / backend changes.

## 5. Non-regression rules

- Do not change drawing IndexedDB key or replay WS protocol.
- Do not repurpose `chartLayoutStore`.
- 1×1 layout must behave like today's single chart (active pane = sole pane).
