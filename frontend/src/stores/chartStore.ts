import { create } from 'zustand'
import {
  CHART_SHOW_GRID_STORAGE_KEY,
  DEFAULT_SYMBOL_ID,
  DEFAULT_TIMEFRAME,
  type ChartTimeframe,
} from '@/constants/chart'
import type { ChartTimezoneId } from '@/constants/timezone'
import type { Symbol } from '@/types/symbol'
import {
  loadChartTimezonePreference,
  saveChartTimezonePreference,
} from '@/utils/chartTimezone'

function loadShowGridPreference(): boolean {
  const stored = localStorage.getItem(CHART_SHOW_GRID_STORAGE_KEY)
  if (stored === 'false') {
    return false
  }
  return true
}

type SymbolBridge = ((symbol: Symbol) => void) | null
type TimeframeBridge = ((timeframe: ChartTimeframe) => void) | null

let symbolBridge: SymbolBridge = null
let timeframeBridge: TimeframeBridge = null

/** WorkspaceRoot registers write-back into active pane / sync fan-out. */
export function registerChartWorkspaceBridge(bridges: {
  onSymbol?: SymbolBridge
  onTimeframe?: TimeframeBridge
}): void {
  symbolBridge = bridges.onSymbol ?? null
  timeframeBridge = bridges.onTimeframe ?? null
}

interface ChartState {
  // Structured Symbol entity (D-86) — API calls use symbol.id, never raw ticker strings.
  symbol: Symbol | null
  timeframe: ChartTimeframe
  timezone: ChartTimezoneId
  showGrid: boolean
  showVolume: boolean
  zoomControlsPulse: number
  /** UX toggle for replay mode (separate from replayStore.phase). */
  replayMode: boolean
  setSymbol: (symbol: Symbol) => void
  setTimeframe: (timeframe: ChartTimeframe) => void
  setTimezone: (timezone: ChartTimezoneId) => void
  setShowGrid: (showGrid: boolean) => void
  setShowVolume: (showVolume: boolean) => void
  pulseZoomControls: () => void
  setReplayMode: (on: boolean) => void
  /** Apply pane values without re-entering the workspace bridge. */
  applyPaneState: (symbol: Symbol | null, timeframe: ChartTimeframe) => void
}

export const useChartStore = create<ChartState>((set) => ({
  symbol: null,
  timeframe: DEFAULT_TIMEFRAME,
  timezone: loadChartTimezonePreference(),
  showGrid: loadShowGridPreference(),
  showVolume: true,
  zoomControlsPulse: 0,
  replayMode: false,
  setSymbol: (symbol) => {
    set({ symbol })
    symbolBridge?.(symbol)
  },
  setTimeframe: (timeframe) => {
    set({ timeframe })
    timeframeBridge?.(timeframe)
  },
  setTimezone: (timezone) => {
    saveChartTimezonePreference(timezone)
    set({ timezone })
  },
  setShowGrid: (showGrid) => {
    localStorage.setItem(CHART_SHOW_GRID_STORAGE_KEY, String(showGrid))
    set({ showGrid })
  },
  setShowVolume: (showVolume) => set({ showVolume }),
  pulseZoomControls: () =>
    set((state) => ({ zoomControlsPulse: state.zoomControlsPulse + 1 })),
  setReplayMode: (on) => set({ replayMode: on }),
  applyPaneState: (symbol, timeframe) => set({ symbol, timeframe }),
}))

export const defaultSymbolId = DEFAULT_SYMBOL_ID
