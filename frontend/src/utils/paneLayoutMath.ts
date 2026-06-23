import {
  DEFAULT_SUB_PANE_CHART_HEIGHT,
  MAX_SUB_PANE_CHART_HEIGHT,
  MIN_MAIN_PANE_HEIGHT,
  MIN_SUB_PANE_CHART_HEIGHT,
  PANE_RESIZE_HANDLE_HEIGHT,
  SUB_PANE_TAB_HEIGHT,
} from '@/constants/chart'

function clampSubHeight(height: number): number {
  return Math.max(MIN_SUB_PANE_CHART_HEIGHT, Math.min(MAX_SUB_PANE_CHART_HEIGHT, height))
}

export function subPaneFixedOverhead(paneCount: number): number {
  if (paneCount <= 0) {
    return 0
  }
  return paneCount * (SUB_PANE_TAB_HEIGHT + PANE_RESIZE_HANDLE_HEIGHT)
}

export function sumSubChartHeights(
  keys: string[],
  heights: Record<string, number>,
): number {
  return keys.reduce((sum, key) => sum + (heights[key] ?? DEFAULT_SUB_PANE_CHART_HEIGHT), 0)
}

export function computeMainPaneHeight(
  layoutHeight: number,
  visibleKeys: string[],
  subPaneHeights: Record<string, number>,
): number {
  if (layoutHeight <= 0) {
    return MIN_MAIN_PANE_HEIGHT
  }
  if (visibleKeys.length === 0) {
    return layoutHeight
  }
  const subsBlock =
    subPaneFixedOverhead(visibleKeys.length) + sumSubChartHeights(visibleKeys, subPaneHeights)
  return Math.max(MIN_MAIN_PANE_HEIGHT, layoutHeight - subsBlock)
}

/** Drag down (positive deltaY) shrinks the sub-pane below the handle; main grows. */
export function nextSubHeightAfterMainResize(
  currentSub: number,
  deltaY: number,
  currentMain: number,
): number | null {
  if (deltaY === 0) {
    return null
  }

  const applied =
    deltaY > 0
      ? Math.min(deltaY, currentSub - MIN_SUB_PANE_CHART_HEIGHT)
      : Math.max(
          deltaY,
          -(MAX_SUB_PANE_CHART_HEIGHT - currentSub),
          -(currentMain - MIN_MAIN_PANE_HEIGHT),
        )

  if (applied === 0) {
    return null
  }

  return clampSubHeight(currentSub - applied)
}

/** Drag down (positive deltaY) grows the top sub-pane and shrinks the bottom one. */
export function nextSubPairHeightsAfterResize(
  top: number,
  bottom: number,
  deltaY: number,
): { top: number; bottom: number } | null {
  if (deltaY === 0) {
    return null
  }

  const applied =
    deltaY > 0
      ? Math.min(deltaY, MAX_SUB_PANE_CHART_HEIGHT - top, bottom - MIN_SUB_PANE_CHART_HEIGHT)
      : Math.max(deltaY, -(top - MIN_SUB_PANE_CHART_HEIGHT), -(MAX_SUB_PANE_CHART_HEIGHT - bottom))

  if (applied === 0) {
    return null
  }

  return {
    top: top + applied,
    bottom: bottom - applied,
  }
}
