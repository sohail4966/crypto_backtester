import { get as idbGet, set as idbSet, del as idbDel } from 'idb-keyval'
import {
  DEFAULT_SYNC_CONFIG,
  LAYOUT_PRESET_PANE_COUNT,
  THEME_BOOT_STORAGE_KEY,
  WORKSPACE_CACHE_KEY,
  WORKSPACE_CACHE_VERSION,
  createDefaultPane,
  createPaneId,
} from '@/constants/workspace'
import { DEFAULT_TIMEFRAME, TIMEFRAME_OPTIONS } from '@/constants/chart'
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

const LAYOUT_PRESETS: ReadonlySet<LayoutPreset> = new Set([
  '1x1',
  '1x2',
  '2x2',
  '1plus2',
])

const TIMEFRAMES: ReadonlySet<string> = new Set(TIMEFRAME_OPTIONS)

function isTheme(value: unknown): value is Theme {
  return value === 'dark' || value === 'light'
}

function isSymbol(value: unknown): value is Symbol {
  if (!value || typeof value !== 'object') {
    return false
  }
  const row = value as Record<string, unknown>
  return (
    typeof row.id === 'string' &&
    typeof row.ticker === 'string' &&
    typeof row.exchange === 'string' &&
    typeof row.baseAsset === 'string' &&
    typeof row.quoteAsset === 'string' &&
    typeof row.tickSize === 'number' &&
    typeof row.lotSize === 'number' &&
    (row.type === 'spot' || row.type === 'perp' || row.type === 'futures') &&
    typeof row.active === 'boolean' &&
    typeof row.sortOrder === 'number'
  )
}

function isPane(value: unknown): value is WorkspacePane {
  if (!value || typeof value !== 'object') {
    return false
  }
  const row = value as Record<string, unknown>
  if (typeof row.id !== 'string') {
    return false
  }
  if (typeof row.timeframe !== 'string' || !TIMEFRAMES.has(row.timeframe)) {
    return false
  }
  if (row.symbol !== null && !isSymbol(row.symbol)) {
    return false
  }
  return true
}

function isLayout(value: unknown): value is ChartLayout {
  if (!value || typeof value !== 'object') {
    return false
  }
  const row = value as Record<string, unknown>
  if (typeof row.id !== 'string' || typeof row.name !== 'string') {
    return false
  }
  if (typeof row.preset !== 'string' || !LAYOUT_PRESETS.has(row.preset as LayoutPreset)) {
    return false
  }
  if (!Array.isArray(row.panes) || row.panes.length === 0) {
    return false
  }
  const expected = LAYOUT_PRESET_PANE_COUNT[row.preset as LayoutPreset]
  if (row.panes.length !== expected) {
    return false
  }
  return row.panes.every(isPane)
}

function isSyncConfig(value: unknown): value is SyncConfig {
  if (!value || typeof value !== 'object') {
    return false
  }
  const row = value as Record<string, unknown>
  return (
    typeof row.crosshair === 'boolean' &&
    typeof row.visibleRange === 'boolean' &&
    typeof row.symbol === 'boolean' &&
    typeof row.timeframe === 'boolean'
  )
}

export function isValidWorkspaceCache(value: unknown): value is WorkspaceCacheV1 {
  if (!value || typeof value !== 'object') {
    return false
  }
  const row = value as Record<string, unknown>
  if (row.version !== WORKSPACE_CACHE_VERSION) {
    return false
  }
  if (typeof row.savedAt !== 'string') {
    return false
  }
  if (!isTheme(row.theme)) {
    return false
  }
  if (typeof row.activeLayoutId !== 'string' || typeof row.activePaneId !== 'string') {
    return false
  }
  if (!Array.isArray(row.layouts) || row.layouts.length === 0) {
    return false
  }
  if (!row.layouts.every(isLayout)) {
    return false
  }
  if (!isSyncConfig(row.sync)) {
    return false
  }
  return true
}

export function readThemeBootHint(): Theme {
  try {
    const stored = globalThis.localStorage?.getItem(THEME_BOOT_STORAGE_KEY)
    return stored === 'light' ? 'light' : 'dark'
  } catch {
    return 'dark'
  }
}

export function writeThemeBootHint(theme: Theme): void {
  try {
    globalThis.localStorage?.setItem(THEME_BOOT_STORAGE_KEY, theme)
  } catch {
    // Ignore quota / private-mode errors.
  }
}

export function createDefaultWorkspace(theme?: Theme): WorkspaceCacheV1 {
  const pane = createDefaultPane(DEFAULT_TIMEFRAME)
  const layout: ChartLayout = {
    id: 'layout-default',
    name: 'Default',
    preset: '1x1',
    panes: [pane],
  }
  return {
    version: WORKSPACE_CACHE_VERSION,
    savedAt: new Date().toISOString(),
    theme: theme ?? readThemeBootHint(),
    activeLayoutId: layout.id,
    activePaneId: pane.id,
    layouts: [layout],
    sync: { ...DEFAULT_SYNC_CONFIG },
  }
}

export function normalizeWorkspaceIds(cache: WorkspaceCacheV1): WorkspaceCacheV1 {
  let layouts = cache.layouts
  let activeLayout = layouts.find((layout) => layout.id === cache.activeLayoutId) ?? layouts[0]
  if (!activeLayout) {
    return createDefaultWorkspace(cache.theme)
  }
  if (activeLayout.id !== cache.activeLayoutId) {
    layouts = layouts.map((layout) =>
      layout.id === activeLayout.id ? layout : layout,
    )
  }
  const activePane =
    activeLayout.panes.find((pane) => pane.id === cache.activePaneId) ??
    activeLayout.panes[0]
  return {
    ...cache,
    activeLayoutId: activeLayout.id,
    activePaneId: activePane.id,
    layouts,
    sync: { ...DEFAULT_SYNC_CONFIG, ...cache.sync },
  }
}

export async function readWorkspaceCache(): Promise<WorkspaceCacheV1 | null> {
  const raw = await idbGet(WORKSPACE_CACHE_KEY)
  if (raw == null) {
    return null
  }
  if (!isValidWorkspaceCache(raw)) {
    await idbDel(WORKSPACE_CACHE_KEY)
    return null
  }
  return normalizeWorkspaceIds(raw)
}

export async function writeWorkspaceCache(
  payload: Omit<WorkspaceCacheV1, 'version' | 'savedAt'> & {
    version?: 1
    savedAt?: string
  },
): Promise<void> {
  const cache: WorkspaceCacheV1 = normalizeWorkspaceIds({
    version: WORKSPACE_CACHE_VERSION,
    savedAt: new Date().toISOString(),
    theme: payload.theme,
    activeLayoutId: payload.activeLayoutId,
    activePaneId: payload.activePaneId,
    layouts: payload.layouts,
    sync: payload.sync,
  })
  if (!isValidWorkspaceCache(cache)) {
    throw new Error('Refusing to persist invalid workspace cache')
  }
  await idbSet(WORKSPACE_CACHE_KEY, cache)
  writeThemeBootHint(cache.theme)
}

export async function deleteWorkspaceCache(): Promise<void> {
  await idbDel(WORKSPACE_CACHE_KEY)
}

export function resizePanesForPreset(
  panes: WorkspacePane[],
  preset: LayoutPreset,
  seed?: WorkspacePane,
): WorkspacePane[] {
  const count = LAYOUT_PRESET_PANE_COUNT[preset]
  const template = seed ?? panes[0] ?? createDefaultPane()
  const next = panes.slice(0, count).map((pane) => ({ ...pane }))
  while (next.length < count) {
    next.push({
      id: createPaneId(),
      symbol: template.symbol ? { ...template.symbol } : null,
      timeframe: template.timeframe,
    })
  }
  return next
}

export function isChartTimeframe(value: string): value is ChartTimeframe {
  return TIMEFRAMES.has(value)
}
