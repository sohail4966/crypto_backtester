import type { ChartTimeframe } from '@/constants/chart'
import { DEFAULT_TIMEFRAME } from '@/constants/chart'
import type { LayoutPreset, SyncConfig, WorkspacePane } from '@/types/workspace'

export const WORKSPACE_CACHE_VERSION = 1
export const WORKSPACE_CACHE_KEY = 'workspace:v1'
export const WORKSPACE_PERSIST_DEBOUNCE_MS = 400
export const THEME_BOOT_STORAGE_KEY = 'cb-theme'

export const DEFAULT_SYNC_CONFIG: SyncConfig = {
  crosshair: true,
  visibleRange: true,
  symbol: false,
  timeframe: false,
}

export const LAYOUT_PRESET_PANE_COUNT: Record<LayoutPreset, number> = {
  '1x1': 1,
  '1x2': 2,
  '2x2': 4,
  '1plus2': 3,
}

export const LAYOUT_PRESET_ORDER: LayoutPreset[] = [
  '1x1',
  '1x2',
  '2x2',
  '1plus2',
]

export const LAYOUT_PRESET_LABELS: Record<LayoutPreset, string> = {
  '1x1': '1×1',
  '1x2': '1×2',
  '2x2': '2×2',
  '1plus2': '1+2',
}

/** Alt+1..4 mapping */
export const LAYOUT_PRESET_BY_ALT_DIGIT: Record<string, LayoutPreset> = {
  '1': '1x1',
  '2': '1x2',
  '3': '2x2',
  '4': '1plus2',
}

export function createPaneId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `pane-${crypto.randomUUID()}`
  }
  return `pane-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

export function createDefaultPane(
  timeframe: ChartTimeframe = DEFAULT_TIMEFRAME,
): WorkspacePane {
  return {
    id: createPaneId(),
    symbol: null,
    timeframe,
  }
}
