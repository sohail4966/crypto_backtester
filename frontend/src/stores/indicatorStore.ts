import { create } from 'zustand'
import {
  isMacdKey,
  MACD_KEYS,
  type ActiveIndicator,
  type IndicatorCatalogEntry,
  type IndicatorPane,
  type IndicatorSpec,
} from '@/types/indicator'
import { indicatorSeriesId, macdSpecs } from '@/utils/indicatorId'

function newInstanceId(): string {
  return crypto.randomUUID()
}

function buildActiveIndicator(
  key: string,
  params: Record<string, unknown>,
  pane: IndicatorPane,
): ActiveIndicator {
  return {
    instanceId: newInstanceId(),
    key: key.toUpperCase(),
    params,
    pane,
    seriesId: indicatorSeriesId(key, params),
  }
}

function expandCatalogEntry(entry: IndicatorCatalogEntry): ActiveIndicator[] {
  const params = { ...entry.defaultParams }
  const pane = entry.pane

  if (isMacdKey(entry.key)) {
    return MACD_KEYS.map((key) => buildActiveIndicator(key, params, 'subchart'))
  }

  return [buildActiveIndicator(entry.key, params, pane)]
}

interface IndicatorState {
  active: ActiveIndicator[]
  addFromCatalog: (entry: IndicatorCatalogEntry) => void
  remove: (instanceId: string) => void
  clear: () => void
  getSpecs: () => IndicatorSpec[]
  getOverlaySeriesIds: () => string[]
  getSubchartGroups: () => ActiveIndicator[][]
}

export const useIndicatorStore = create<IndicatorState>((set, get) => ({
  active: [],

  addFromCatalog: (entry) => {
    const next = expandCatalogEntry(entry)
    const existingIds = new Set(get().active.map((item) => item.seriesId))
    const toAdd = next.filter((item) => !existingIds.has(item.seriesId))
    if (toAdd.length === 0) {
      return
    }
    set((state) => ({ active: [...state.active, ...toAdd] }))
  },

  remove: (instanceId) => {
    set((state) => {
      const target = state.active.find((item) => item.instanceId === instanceId)
      if (!target) {
        return state
      }

      // Removing any MACD leg removes the whole MACD bundle.
      if (isMacdKey(target.key)) {
        const macdIds = new Set(
          MACD_KEYS.map((key) => indicatorSeriesId(key, target.params)),
        )
        return {
          active: state.active.filter((item) => !macdIds.has(item.seriesId)),
        }
      }

      return {
        active: state.active.filter((item) => item.instanceId !== instanceId),
      }
    })
  },

  clear: () => set({ active: [] }),

  getSpecs: () => {
    const seen = new Set<string>()
    const specs: IndicatorSpec[] = []
    for (const item of get().active) {
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
      .active.filter((item) => item.pane === 'overlay')
      .map((item) => item.seriesId),

  getSubchartGroups: () => {
    const subcharts = get().active.filter((item) => item.pane === 'subchart')
    const groups = new Map<string, ActiveIndicator[]>()
    for (const item of subcharts) {
      const groupKey = isMacdKey(item.key)
        ? `MACD:${JSON.stringify(item.params)}`
        : item.seriesId
      const list = groups.get(groupKey) ?? []
      list.push(item)
      groups.set(groupKey, list)
    }
    return [...groups.values()]
  },
}))

export { macdSpecs }
