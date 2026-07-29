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

interface IndicatorState {
  active: ActiveIndicator[]
  settingsInstanceId: string | null
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

export const useIndicatorStore = create<IndicatorState>((set, get) => ({
  active: [],
  settingsInstanceId: null,

  addFromCatalog: (entry, patch) => {
    if (entry.pane === 'subchart' && countSubchartInstances(get().active) >= MAX_SUB_PANES) {
      return {
        ok: false,
        error: `Maximum ${MAX_SUB_PANES} sub-chart panes allowed. Remove one to add another.`,
      }
    }

    const toAdd = expandCatalogEntry(entry, patch ?? {})
    const groupInstanceId = toAdd[0]?.groupInstanceId
    set((state) => ({ active: [...state.active, ...toAdd] }))
    if (entry.pane === 'subchart' && groupInstanceId) {
      useChartLayoutStore.getState().initSubPane(groupInstanceId)
    }
    return { ok: true }
  },

  remove: (instanceId) => {
    set((state) => {
      const target = state.active.find((item) => item.instanceId === instanceId)
      if (!target) {
        return state
      }

      const { groupInstanceId } = target
      useChartLayoutStore.getState().removeSubPane(groupInstanceId)
      return {
        active: state.active.filter((item) => item.groupInstanceId !== groupInstanceId),
      }
    })
  },

  toggleVisible: (instanceId) => {
    set((state) => {
      const target = state.active.find((item) => item.instanceId === instanceId)
      if (!target) {
        return state
      }
      const { groupInstanceId } = target
      const members = state.active.filter((item) => item.groupInstanceId === groupInstanceId)
      const anyVisible = members.some((item) => item.visible !== false)
      const nextVisible = !anyVisible
      return {
        active: state.active.map((item) =>
          item.groupInstanceId === groupInstanceId ? { ...item, visible: nextVisible } : item,
        ),
      }
    })
  },

  openSettings: (instanceId) => set({ settingsInstanceId: instanceId }),

  closeSettings: () => set({ settingsInstanceId: null }),

  updateParams: (instanceId, params) =>
    get().updateIndicatorSettings(instanceId, { params }),

  updateIndicatorSettings: (instanceId, patch) => {
    const state = get()
    const target = state.active.find((item) => item.instanceId === instanceId)
    if (!target) {
      return { ok: false, error: 'Indicator not found' }
    }

    const { groupInstanceId } = target
    const nextParams = patch.params ?? target.params

    set({
      active: state.active.map((item) => {
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
      }),
    })

    return { ok: true }
  },

  clear: () => set({ active: [], settingsInstanceId: null }),
}))
