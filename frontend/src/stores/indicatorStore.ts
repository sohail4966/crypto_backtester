import { create } from 'zustand'
import {
  type ActiveIndicator,
  type IndicatorCatalogEntry,
  type IndicatorPane,
} from '@/types/indicator'
import { bundleKeysFor } from '@/utils/indicatorCatalog'
import { defaultBundleSeriesColor } from '@/utils/indicatorDisplay'
import { indicatorSeriesId } from '@/utils/indicatorId'
import { useChartLayoutStore } from '@/stores/chartLayoutStore'
import { MAX_SUB_PANES } from '@/constants/chart'
import {
  writeIndicatorCache,
  type IndicatorCacheV1,
} from '@/services/indicatorCache'

export type UpdateParamsResult = { ok: true } | { ok: false; error: string }
export type AddIndicatorResult = { ok: true } | { ok: false; error: string }

export interface IndicatorAppearance {
  color?: string
  lineWidth?: number
  visible?: boolean
}

export interface IndicatorSettingsPatch {
  params?: Record<string, unknown>
  /** Per registry key (e.g. BB_UPPER) within the instance group. */
  seriesStyles?: Record<string, IndicatorAppearance>
}

const DEFAULT_PANE_ID = 'main'
let persistTimer: ReturnType<typeof setTimeout> | null = null

function countSubchartInstances(active: ActiveIndicator[]): number {
  const ids = new Set<string>()
  for (const item of active) {
    if (item.pane === 'subchart') {
      ids.add(item.groupInstanceId)
    }
  }
  return ids.size
}

function newInstanceId(): string {
  return crypto.randomUUID()
}

function buildActiveIndicator(
  key: string,
  params: Record<string, unknown>,
  pane: IndicatorPane,
  groupInstanceId: string,
  appearance: IndicatorAppearance = {},
): ActiveIndicator {
  return {
    instanceId: newInstanceId(),
    groupInstanceId,
    key: key.toUpperCase(),
    params,
    pane,
    seriesId: indicatorSeriesId(key, params),
    visible: appearance.visible ?? true,
    color: appearance.color,
    lineWidth: appearance.lineWidth,
  }
}

function expandCatalogEntry(
  entry: IndicatorCatalogEntry,
  patch: IndicatorSettingsPatch = {},
): ActiveIndicator[] {
  const params = { ...entry.defaultParams, ...patch.params }
  const pane = entry.pane
  const keys = bundleKeysFor(entry.key)
  const groupInstanceId = newInstanceId()

  return keys.map((key, lineIndex) =>
    buildActiveIndicator(key, params, pane, groupInstanceId, {
      color:
        patch.seriesStyles?.[key]?.color ?? defaultBundleSeriesColor(key, lineIndex),
      lineWidth: patch.seriesStyles?.[key]?.lineWidth ?? 2,
      visible: patch.seriesStyles?.[key]?.visible,
    }),
  )
}

function schedulePersist(byPane: Record<string, ActiveIndicator[]>): void {
  if (persistTimer) {
    clearTimeout(persistTimer)
  }
  persistTimer = setTimeout(() => {
    const payload: IndicatorCacheV1 = {
      version: 1,
      schema: 'byPane',
      savedAt: new Date().toISOString(),
      byPane,
    }
    void writeIndicatorCache(payload)
  }, 400)
}

interface IndicatorState {
  /** Per workspace-pane indicator sets (FE-014). */
  byPane: Record<string, ActiveIndicator[]>
  /** Pane the IndicatorPanel edits (workspace active pane). */
  editingPaneId: string
  /** Convenience mirror of byPane[editingPaneId] for existing callers/tests. */
  active: ActiveIndicator[]
  settingsInstanceId: string | null
  setEditingPaneId: (paneId: string) => void
  indicatorsForPane: (paneId: string) => ActiveIndicator[]
  hydrateFromCache: (cache: IndicatorCacheV1) => void
  addFromCatalog: (
    entry: IndicatorCatalogEntry,
    patch?: IndicatorSettingsPatch,
  ) => AddIndicatorResult
  remove: (instanceId: string) => void
  toggleVisible: (instanceId: string) => void
  openSettings: (instanceId: string) => void
  closeSettings: () => void
  updateParams: (instanceId: string, params: Record<string, unknown>) => UpdateParamsResult
  updateIndicatorSettings: (
    instanceId: string,
    patch: IndicatorSettingsPatch,
  ) => UpdateParamsResult
  clear: () => void
}

function withPaneUpdate(
  state: IndicatorState,
  paneId: string,
  nextForPane: ActiveIndicator[],
): Partial<IndicatorState> {
  const byPane = { ...state.byPane, [paneId]: nextForPane }
  schedulePersist(byPane)
  return {
    byPane,
    active: paneId === state.editingPaneId ? nextForPane : state.active,
  }
}

export const useIndicatorStore = create<IndicatorState>((set, get) => ({
  byPane: { [DEFAULT_PANE_ID]: [] },
  editingPaneId: DEFAULT_PANE_ID,
  active: [],
  settingsInstanceId: null,

  setEditingPaneId: (paneId) => {
    const state = get()
    const active = state.byPane[paneId] ?? []
    set({
      editingPaneId: paneId,
      active,
      byPane: state.byPane[paneId] ? state.byPane : { ...state.byPane, [paneId]: [] },
    })
  },

  indicatorsForPane: (paneId) => get().byPane[paneId] ?? [],

  hydrateFromCache: (cache) => {
    let byPane: Record<string, ActiveIndicator[]> = { [DEFAULT_PANE_ID]: [] }
    if (cache.schema === 'byPane' && cache.byPane) {
      byPane = { ...byPane, ...cache.byPane }
    } else if (cache.active) {
      byPane = { [DEFAULT_PANE_ID]: cache.active }
    }
    const editingPaneId = get().editingPaneId
    set({
      byPane,
      active: byPane[editingPaneId] ?? byPane[DEFAULT_PANE_ID] ?? [],
    })
  },

  addFromCatalog: (entry, patch) => {
    const state = get()
    const paneId = state.editingPaneId
    const current = state.byPane[paneId] ?? []
    if (entry.pane === 'subchart' && countSubchartInstances(current) >= MAX_SUB_PANES) {
      return {
        ok: false,
        error: `Maximum ${MAX_SUB_PANES} sub-chart panes allowed. Remove one to add another.`,
      }
    }

    const toAdd = expandCatalogEntry(entry, patch ?? {})
    const groupInstanceId = toAdd[0]?.groupInstanceId
    const next = [...current, ...toAdd]
    set(withPaneUpdate(state, paneId, next))
    if (entry.pane === 'subchart' && groupInstanceId) {
      useChartLayoutStore.getState().initSubPane(groupInstanceId)
    }
    return { ok: true }
  },

  remove: (instanceId) => {
    set((state) => {
      const paneId = state.editingPaneId
      const current = state.byPane[paneId] ?? []
      const target = current.find((item) => item.instanceId === instanceId)
      if (!target) {
        return state
      }

      const { groupInstanceId } = target
      useChartLayoutStore.getState().removeSubPane(groupInstanceId)
      const next = current.filter((item) => item.groupInstanceId !== groupInstanceId)
      return withPaneUpdate(state, paneId, next)
    })
  },

  toggleVisible: (instanceId) => {
    set((state) => {
      const paneId = state.editingPaneId
      const current = state.byPane[paneId] ?? []
      const target = current.find((item) => item.instanceId === instanceId)
      if (!target) {
        return state
      }
      const { groupInstanceId } = target
      const members = current.filter((item) => item.groupInstanceId === groupInstanceId)
      const anyVisible = members.some((item) => item.visible !== false)
      const nextVisible = !anyVisible
      const next = current.map((item) =>
        item.groupInstanceId === groupInstanceId ? { ...item, visible: nextVisible } : item,
      )
      return withPaneUpdate(state, paneId, next)
    })
  },

  openSettings: (instanceId) => set({ settingsInstanceId: instanceId }),

  closeSettings: () => set({ settingsInstanceId: null }),

  updateParams: (instanceId, params) =>
    get().updateIndicatorSettings(instanceId, { params }),

  updateIndicatorSettings: (instanceId, patch) => {
    const state = get()
    const paneId = state.editingPaneId
    const current = state.byPane[paneId] ?? []
    const target = current.find((item) => item.instanceId === instanceId)
    if (!target) {
      return { ok: false, error: 'Indicator not found' }
    }

    const { groupInstanceId } = target
    const nextParams = patch.params ?? target.params

    const next = current.map((item) => {
      if (item.groupInstanceId !== groupInstanceId) {
        return item
      }
      const seriesStyle = patch.seriesStyles?.[item.key]
      return {
        ...item,
        params: { ...nextParams },
        seriesId: indicatorSeriesId(item.key, nextParams),
        color: seriesStyle?.color !== undefined ? seriesStyle.color : item.color,
        lineWidth:
          seriesStyle?.lineWidth !== undefined ? seriesStyle.lineWidth : item.lineWidth,
        visible:
          seriesStyle?.visible !== undefined ? seriesStyle.visible : item.visible,
      }
    })
    set(withPaneUpdate(state, paneId, next))

    return { ok: true }
  },

  clear: () => {
    if (persistTimer) {
      clearTimeout(persistTimer)
      persistTimer = null
    }
    set({
      byPane: { [DEFAULT_PANE_ID]: [] },
      editingPaneId: DEFAULT_PANE_ID,
      active: [],
      settingsInstanceId: null,
    })
  },
}))
