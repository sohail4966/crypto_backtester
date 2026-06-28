import { useCallback, useEffect, useMemo } from 'react'
import { DEFAULT_SUB_PANE_CHART_HEIGHT } from '@/constants/chart'
import { useChartLayoutStore } from '@/stores/chartLayoutStore'
import type { ActiveIndicator } from '@/types/indicator'
import {
  computeMainPaneHeight,
  nextSubHeightAfterMainResize,
  nextSubPairHeightsAfterResize,
} from '@/utils/paneLayoutMath'

export function subchartGroupKeys(groups: ActiveIndicator[][]): string[] {
  return groups
    .map((group) => group[0]?.groupInstanceId ?? '')
    .filter(Boolean)
}

export function usePaneLayout(
  layoutHeight: number,
  subchartGroups: ActiveIndicator[][],
) {
  const subPaneHeights = useChartLayoutStore((state) => state.subPaneHeights)
  const initSubPane = useChartLayoutStore((state) => state.initSubPane)
  const removeSubPane = useChartLayoutStore((state) => state.removeSubPane)
  const setSubPaneHeight = useChartLayoutStore((state) => state.setSubPaneHeight)
  const setSubPanePairHeights = useChartLayoutStore((state) => state.setSubPanePairHeights)

  const groupKeys = useMemo(() => subchartGroupKeys(subchartGroups), [subchartGroups])

  const chartVisibleKeys = useMemo(
    () =>
      subchartGroupKeys(
        subchartGroups.filter((group) => group.some((item) => item.visible !== false)),
      ),
    [subchartGroups],
  )

  useEffect(() => {
    const keys = new Set(groupKeys)
    for (const key of groupKeys) {
      initSubPane(key)
    }
    for (const key of Object.keys(useChartLayoutStore.getState().subPaneHeights)) {
      if (!keys.has(key)) {
        removeSubPane(key)
      }
    }
  }, [groupKeys, initSubPane, removeSubPane])

  const mainPaneHeight = useMemo(
    () => computeMainPaneHeight(layoutHeight, groupKeys, subPaneHeights, chartVisibleKeys),
    [chartVisibleKeys, groupKeys, layoutHeight, subPaneHeights],
  )

  const onResizeAboveSub = useCallback(
    (groupKey: string, deltaY: number) => {
      const heights = useChartLayoutStore.getState().subPaneHeights
      const currentSub = heights[groupKey] ?? DEFAULT_SUB_PANE_CHART_HEIGHT
      const currentMain = computeMainPaneHeight(layoutHeight, groupKeys, heights, chartVisibleKeys)
      const nextSub = nextSubHeightAfterMainResize(currentSub, deltaY, currentMain)
      if (nextSub != null) {
        setSubPaneHeight(groupKey, nextSub)
      }
    },
    [chartVisibleKeys, groupKeys, layoutHeight, setSubPaneHeight],
  )

  const onResizeBetweenSubs = useCallback(
    (topKey: string, bottomKey: string, deltaY: number) => {
      const heights = useChartLayoutStore.getState().subPaneHeights
      const top = heights[topKey] ?? DEFAULT_SUB_PANE_CHART_HEIGHT
      const bottom = heights[bottomKey] ?? DEFAULT_SUB_PANE_CHART_HEIGHT
      const next = nextSubPairHeightsAfterResize(top, bottom, deltaY)
      if (next) {
        setSubPanePairHeights(topKey, bottomKey, next.top, next.bottom)
      }
    },
    [setSubPanePairHeights],
  )

  return {
    mainPaneHeight,
    groupKeys,
    getSubChartHeight: (groupKey: string) =>
      subPaneHeights[groupKey] ?? DEFAULT_SUB_PANE_CHART_HEIGHT,
    onResizeAboveSub,
    onResizeBetweenSubs,
  }
}
