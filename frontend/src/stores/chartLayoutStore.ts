import { create } from 'zustand'
import {
  DEFAULT_SUB_PANE_CHART_HEIGHT,
  MAX_SUB_PANE_CHART_HEIGHT,
  MIN_SUB_PANE_CHART_HEIGHT,
} from '@/constants/chart'

function clampSubHeight(height: number): number {
  return Math.max(MIN_SUB_PANE_CHART_HEIGHT, Math.min(MAX_SUB_PANE_CHART_HEIGHT, height))
}

interface ChartLayoutState {
  subPaneHeights: Record<string, number>
  initSubPane: (groupKey: string) => void
  removeSubPane: (groupKey: string) => void
  renameSubPane: (fromKey: string, toKey: string) => void
  setSubPaneHeight: (groupKey: string, height: number) => void
  setSubPanePairHeights: (topKey: string, bottomKey: string, top: number, bottom: number) => void
  getSubPaneChartHeight: (groupKey: string) => number
}

export const useChartLayoutStore = create<ChartLayoutState>((set, get) => ({
  subPaneHeights: {},

  initSubPane: (groupKey) => {
    if (get().subPaneHeights[groupKey] != null) {
      return
    }
    set((state) => ({
      subPaneHeights: {
        ...state.subPaneHeights,
        [groupKey]: DEFAULT_SUB_PANE_CHART_HEIGHT,
      },
    }))
  },

  removeSubPane: (groupKey) => {
    set((state) => {
      const next = { ...state.subPaneHeights }
      delete next[groupKey]
      return { subPaneHeights: next }
    })
  },

  setSubPaneHeight: (groupKey, height) => {
    const next = clampSubHeight(height)
    const current = get().subPaneHeights[groupKey] ?? DEFAULT_SUB_PANE_CHART_HEIGHT
    if (current === next) {
      return
    }
    set((state) => ({
      subPaneHeights: {
        ...state.subPaneHeights,
        [groupKey]: next,
      },
    }))
  },

  setSubPanePairHeights: (topKey, bottomKey, top, bottom) => {
    const nextTop = clampSubHeight(top)
    const nextBottom = clampSubHeight(bottom)
    const state = get()
    const prevTop = state.subPaneHeights[topKey] ?? DEFAULT_SUB_PANE_CHART_HEIGHT
    const prevBottom = state.subPaneHeights[bottomKey] ?? DEFAULT_SUB_PANE_CHART_HEIGHT
    if (prevTop === nextTop && prevBottom === nextBottom) {
      return
    }
    set((s) => ({
      subPaneHeights: {
        ...s.subPaneHeights,
        [topKey]: nextTop,
        [bottomKey]: nextBottom,
      },
    }))
  },

  getSubPaneChartHeight: (groupKey) =>
    get().subPaneHeights[groupKey] ?? DEFAULT_SUB_PANE_CHART_HEIGHT,

  renameSubPane: (fromKey, toKey) => {
    if (fromKey === toKey) {
      return
    }
    set((state) => {
      const height = state.subPaneHeights[fromKey]
      if (height == null) {
        return state
      }
      const next = { ...state.subPaneHeights }
      delete next[fromKey]
      next[toKey] = height
      return { subPaneHeights: next }
    })
  },
}))
