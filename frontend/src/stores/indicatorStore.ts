import { create } from 'zustand'
import {
  type ActiveIndicator,
  type IndicatorCatalogEntry,
  type IndicatorPane,
  type IndicatorSpec,
} from '@/types/indicator'
import { bundleGroupKey, bundleKeysFor } from '@/utils/indicatorCatalog'
import { indicatorSeriesId, macdSpecs } from '@/utils/indicatorId'
import { useChartLayoutStore } from '@/stores/chartLayoutStore'
import { MAX_SUB_PANES } from '@/constants/chart'

export type UpdateParamsResult = { ok: true } | { ok: false; error: string }
export type AddIndicatorResult = { ok: true } | { ok: false; error: string }

function countSubchartGroups(active: ActiveIndicator[]): number {
  const keys = new Set<string>()
  for (const item of active) {
    if (item.pane === 'subchart') {
      keys.add(bundleGroupKey(item.key, item.params))
    }
  }
  return keys.size
}

function newInstanceId(): string {
  return crypto.randomUUID()
}

function buildActiveIndicator(
  key: string,
  params: Record<string, unknown>,
  pane: IndicatorPane,
  visible = true,
): ActiveIndicator {
  return {
    instanceId: newInstanceId(),
    key: key.toUpperCase(),
    params,
    pane,
    seriesId: indicatorSeriesId(key, params),
    visible,
  }
}

function expandCatalogEntry(entry: IndicatorCatalogEntry): ActiveIndicator[] {
  const params = { ...entry.defaultParams }
  const pane = entry.pane
  const keys = bundleKeysFor(entry.key)

  return keys.map((key) => buildActiveIndicator(key, params, pane))
}

interface IndicatorState {
  active: ActiveIndicator[]
  settingsInstanceId: string | null
  addFromCatalog: (entry: IndicatorCatalogEntry) => AddIndicatorResult
  remove: (instanceId: string) => void
  toggleVisible: (instanceId: string) => void
  openSettings: (instanceId: string) => void
  closeSettings: () => void
  isGroupVisible: (instanceId: string) => boolean
  updateParams: (instanceId: string, params: Record<string, unknown>) => UpdateParamsResult
  clear: () => void
  getSpecs: () => IndicatorSpec[]
  getOverlaySeriesIds: () => string[]
  getSubchartGroups: () => ActiveIndicator[][]
}

export const useIndicatorStore = create<IndicatorState>((set, get) => ({
  active: [],
  settingsInstanceId: null,

  addFromCatalog: (entry) => {
    const groupKey = bundleGroupKey(entry.key, entry.defaultParams)
    const alreadyActive = get().active.some(
      (item) => bundleGroupKey(item.key, item.params) === groupKey,
    )

    if (entry.pane === 'subchart' && !alreadyActive) {
      if (countSubchartGroups(get().active) >= MAX_SUB_PANES) {
        return {
          ok: false,
          error: `Maximum ${MAX_SUB_PANES} sub-chart panes allowed. Remove one to add another.`,
        }
      }
    }

    const next = expandCatalogEntry(entry)
    const existingIds = new Set(get().active.map((item) => item.seriesId))
    const toAdd = next.filter((item) => !existingIds.has(item.seriesId))
    if (toAdd.length === 0) {
      return { ok: true }
    }
    set((state) => ({ active: [...state.active, ...toAdd] }))
    if (entry.pane === 'subchart') {
      useChartLayoutStore.getState().initSubPane(groupKey)
    }
    return { ok: true }
  },

  remove: (instanceId) => {
    set((state) => {
      const target = state.active.find((item) => item.instanceId === instanceId)
      if (!target) {
        return state
      }

      const groupKey = bundleGroupKey(target.key, target.params)
      useChartLayoutStore.getState().removeSubPane(groupKey)
      return {
        active: state.active.filter(
          (item) => bundleGroupKey(item.key, item.params) !== groupKey,
        ),
      }
    })
  },

  toggleVisible: (instanceId) => {
    set((state) => {
      const target = state.active.find((item) => item.instanceId === instanceId)
      if (!target) {
        return state
      }
      const groupKey = bundleGroupKey(target.key, target.params)
      const nextVisible = target.visible === false ? true : false
      return {
        active: state.active.map((item) =>
          bundleGroupKey(item.key, item.params) === groupKey
            ? { ...item, visible: nextVisible }
            : item,
        ),
      }
    })
  },

  isGroupVisible: (instanceId) => {
    const target = get().active.find((item) => item.instanceId === instanceId)
    return target?.visible !== false
  },

  openSettings: (instanceId) => set({ settingsInstanceId: instanceId }),
  closeSettings: () => set({ settingsInstanceId: null }),

  updateParams: (instanceId, params) => {
    const state = get()
    const target = state.active.find((item) => item.instanceId === instanceId)
    if (!target) {
      return { ok: false, error: 'Indicator not found' }
    }

    const groupKey = bundleGroupKey(target.key, target.params)
    const toUpdate = state.active.filter(
      (item) => bundleGroupKey(item.key, item.params) === groupKey,
    )

    const nextSeriesIds = toUpdate.map((item) => indicatorSeriesId(item.key, params))
    const otherSeriesIds = new Set(
      state.active
        .filter((item) => bundleGroupKey(item.key, item.params) !== groupKey)
        .map((item) => item.seriesId),
    )

    if (nextSeriesIds.some((id) => otherSeriesIds.has(id))) {
      return { ok: false, error: 'An indicator with these settings is already on the chart' }
    }

    set({
      active: state.active.map((item) => {
        if (bundleGroupKey(item.key, item.params) !== groupKey) {
          return item
        }
        return {
          ...item,
          params: { ...params },
          seriesId: indicatorSeriesId(item.key, params),
          visible: item.visible,
        }
      }),
    })

    return { ok: true }
  },

  clear: () => set({ active: [] }),

  getSpecs: () => {
    const seen = new Set<string>()
    const specs: IndicatorSpec[] = []
    for (const item of get().active) {
      if (item.visible === false) {
        continue
      }
      const id = `${item.key}:${JSON.stringify(item.params)}:${item.pane}`
      if (seen.has(id)) {
        continue
      }
      seen.add(id)
      specs.push({ key: item.key, params: item.params, pane: item.pane })
    }
    return specs
  },

  getOverlaySeriesIds: () =>
    get()
      .active.filter((item) => item.pane === 'overlay' && item.visible !== false)
      .map((item) => item.seriesId),

  getSubchartGroups: () => {
    const subcharts = get().active.filter((item) => item.pane === 'subchart')
    const groups = new Map<string, ActiveIndicator[]>()
    for (const item of subcharts) {
      const groupKey = bundleGroupKey(item.key, item.params)
      const list = groups.get(groupKey) ?? []
      list.push(item)
      groups.set(groupKey, list)
    }
    return [...groups.values()]
  },
}))

export { macdSpecs }
