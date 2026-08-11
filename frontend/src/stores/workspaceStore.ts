import { create } from 'zustand'
import {
  DEFAULT_SYNC_CONFIG,
  LAYOUT_PRESET_LABELS,
  createDefaultPane,
} from '@/constants/workspace'
import type { ChartTimeframe } from '@/constants/chart'
import type { Theme } from '@/types/theme'
import type { Symbol } from '@/types/symbol'
import type {
  ChartLayout,
  LayoutPreset,
  SyncConfig,
  WorkspaceCacheV1,
  WorkspacePane,
} from '@/types/workspace'
import {
  createDefaultWorkspace,
  normalizeWorkspaceIds,
  resizePanesForPreset,
} from '@/services/workspaceStorage'

interface WorkspaceState {
  hydrated: boolean
  theme: Theme
  layouts: ChartLayout[]
  activeLayoutId: string
  activePaneId: string
  sync: SyncConfig
  hydrate: (cache: WorkspaceCacheV1) => void
  setTheme: (theme: Theme) => void
  setLayoutPreset: (preset: LayoutPreset) => void
  setActivePaneId: (paneId: string) => void
  setSyncCategory: <K extends keyof SyncConfig>(key: K, value: SyncConfig[K]) => void
  updateActivePaneSymbol: (symbol: Symbol) => void
  updateActivePaneTimeframe: (timeframe: ChartTimeframe) => void
  applySymbolToPanes: (symbol: Symbol, all: boolean) => void
  applyTimeframeToPanes: (timeframe: ChartTimeframe, all: boolean) => void
  getActiveLayout: () => ChartLayout | null
  getActivePane: () => WorkspacePane | null
  toPersistPayload: () => Omit<WorkspaceCacheV1, 'version' | 'savedAt'>
}

function ensureLayout(state: WorkspaceState): ChartLayout {
  const found =
    state.layouts.find((layout) => layout.id === state.activeLayoutId) ??
    state.layouts[0]
  if (!found) {
    return createDefaultWorkspace(state.theme).layouts[0]
  }
  return found
}

export const useWorkspaceStore = create<WorkspaceState>((set, get) => {
  const defaults = createDefaultWorkspace()

  return {
    hydrated: false,
    theme: defaults.theme,
    layouts: defaults.layouts,
    activeLayoutId: defaults.activeLayoutId,
    activePaneId: defaults.activePaneId,
    sync: { ...DEFAULT_SYNC_CONFIG },

    hydrate: (cache) => {
      const normalized = normalizeWorkspaceIds(cache)
      set({
        hydrated: true,
        theme: normalized.theme,
        layouts: normalized.layouts,
        activeLayoutId: normalized.activeLayoutId,
        activePaneId: normalized.activePaneId,
        sync: normalized.sync,
      })
    },

    setTheme: (theme) => set({ theme }),

    setLayoutPreset: (preset) => {
      set((state) => {
        const layout = ensureLayout(state)
        const seed =
          layout.panes.find((pane) => pane.id === state.activePaneId) ??
          layout.panes[0] ??
          createDefaultPane()
        const panes = resizePanesForPreset(layout.panes, preset, seed)
        const activePaneId = panes.some((pane) => pane.id === state.activePaneId)
          ? state.activePaneId
          : panes[0].id
        const nextLayout: ChartLayout = {
          ...layout,
          preset,
          name: LAYOUT_PRESET_LABELS[preset],
          panes,
        }
        return {
          layouts: state.layouts.map((item) =>
            item.id === nextLayout.id ? nextLayout : item,
          ),
          activePaneId,
        }
      })
    },

    setActivePaneId: (paneId) => {
      const layout = ensureLayout(get())
      if (!layout.panes.some((pane) => pane.id === paneId)) {
        return
      }
      set({ activePaneId: paneId })
    },

    setSyncCategory: (key, value) => {
      set((state) => ({
        sync: { ...state.sync, [key]: value },
      }))
    },

    updateActivePaneSymbol: (symbol) => {
      const { sync } = get()
      get().applySymbolToPanes(symbol, sync.symbol)
    },

    updateActivePaneTimeframe: (timeframe) => {
      const { sync } = get()
      get().applyTimeframeToPanes(timeframe, sync.timeframe)
    },

    applySymbolToPanes: (symbol, all) => {
      set((state) => {
        const layout = ensureLayout(state)
        const panes = layout.panes.map((pane) => {
          if (all || pane.id === state.activePaneId) {
            return { ...pane, symbol: { ...symbol } }
          }
          return pane
        })
        return {
          layouts: state.layouts.map((item) =>
            item.id === layout.id ? { ...item, panes } : item,
          ),
        }
      })
    },

    applyTimeframeToPanes: (timeframe, all) => {
      set((state) => {
        const layout = ensureLayout(state)
        const panes = layout.panes.map((pane) => {
          if (all || pane.id === state.activePaneId) {
            return { ...pane, timeframe }
          }
          return pane
        })
        return {
          layouts: state.layouts.map((item) =>
            item.id === layout.id ? { ...item, panes } : item,
          ),
        }
      })
    },

    getActiveLayout: () => ensureLayout(get()),

    getActivePane: () => {
      const state = get()
      const layout = ensureLayout(state)
      return (
        layout.panes.find((pane) => pane.id === state.activePaneId) ??
        layout.panes[0] ??
        null
      )
    },

    toPersistPayload: () => {
      const state = get()
      return {
        theme: state.theme,
        activeLayoutId: state.activeLayoutId,
        activePaneId: state.activePaneId,
        layouts: state.layouts,
        sync: state.sync,
      }
    },
  }
})
