import type { ChartTimeframe } from '@/constants/chart'
import type { Theme } from '@/types/theme'
import type { Symbol } from '@/types/symbol'

export type LayoutPreset = '1x1' | '1x2' | '2x2' | '1plus2'

export interface WorkspacePane {
  id: string
  symbol: Symbol | null
  timeframe: ChartTimeframe
}

export interface ChartLayout {
  id: string
  name: string
  preset: LayoutPreset
  panes: WorkspacePane[]
}

export interface SyncConfig {
  crosshair: boolean
  visibleRange: boolean
  symbol: boolean
  timeframe: boolean
}

export interface WorkspaceCacheV1 {
  version: 1
  savedAt: string
  theme: Theme
  activeLayoutId: string
  activePaneId: string
  layouts: ChartLayout[]
  sync: SyncConfig
}

export type SyncEvent =
  | { type: 'crosshair'; sourcePaneId: string; time: number | null }
  | {
      type: 'visibleRange'
      sourcePaneId: string
      range: { from: number; to: number } | null
    }
  | { type: 'symbol'; sourcePaneId: string; symbol: Symbol }
  | { type: 'timeframe'; sourcePaneId: string; timeframe: ChartTimeframe }
