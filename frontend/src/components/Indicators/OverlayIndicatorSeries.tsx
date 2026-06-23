import { useEffect, useRef } from 'react'
import type { ISeriesApi, LineData } from 'lightweight-charts'
import { useChartContext } from '@/components/Chart/ChartContext'
import { useTheme } from '@/hooks/useTheme'
import type { IndicatorPoint } from '@/types/indicator'
import { isFiniteNumber, toUtcTimestamp } from '@/utils/chartSeriesData'
import { OVERLAY_INDICATOR_COLORS } from '@/utils/indicatorDisplay'
import { resolveChartColor } from '@/utils/color'

interface OverlayIndicatorSeriesProps {
  seriesId: string
  label: string
  points: IndicatorPoint[]
  colorIndex: number
  visible?: boolean
}

export function OverlayIndicatorSeries({
  seriesId,
  label,
  points,
  colorIndex,
  visible = true,
}: OverlayIndicatorSeriesProps) {
  const { chart } = useChartContext()
  const { theme } = useTheme()
  const seriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const color = resolveChartColor(
    OVERLAY_INDICATOR_COLORS[colorIndex % OVERLAY_INDICATOR_COLORS.length],
    theme,
  )

  useEffect(() => {
    if (!chart) {
      return
    }

    const series = chart.addLineSeries({
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true,
    })
    seriesRef.current = series

    return () => {
      chart.removeSeries(series)
      seriesRef.current = null
    }
  }, [chart, seriesId])

  useEffect(() => {
    seriesRef.current?.applyOptions({ color, title: label, visible })
  }, [color, label, visible])

  useEffect(() => {
    const series = seriesRef.current
    if (!series) {
      return
    }

    const data: LineData[] = points
      .flatMap((point) => {
        const time = toUtcTimestamp(point.time)
        if (time == null || !isFiniteNumber(point.value)) {
          return []
        }
        return [{ time, value: point.value }]
      })

    series.setData(data)
  }, [points])

  return null
}
