import { useCallback } from 'react'
import type { IChartApi } from 'lightweight-charts'
import { fitToVisibleBars } from '@/utils/chartViewport'

const ZOOM_FACTOR = 0.75

export function useChartZoom(chart: IChartApi | null, barCount: number) {
  const zoom = useCallback(
    (direction: 'in' | 'out') => {
      if (!chart) {
        return
      }

      const timeScale = chart.timeScale()
      const range = timeScale.getVisibleLogicalRange()
      if (!range) {
        return
      }

      const center = (range.from + range.to) / 2
      const halfSpan = (range.to - range.from) / 2
      const scale = direction === 'in' ? ZOOM_FACTOR : 1 / ZOOM_FACTOR

      timeScale.setVisibleLogicalRange({
        from: center - halfSpan * scale,
        to: center + halfSpan * scale,
      })
    },
    [chart],
  )

  const zoomIn = useCallback(() => zoom('in'), [zoom])
  const zoomOut = useCallback(() => zoom('out'), [zoom])
  const resetZoom = useCallback(() => {
    if (chart && barCount > 0) {
      fitToVisibleBars(chart, barCount)
    }
  }, [barCount, chart])

  return { zoomIn, zoomOut, resetZoom }
}
