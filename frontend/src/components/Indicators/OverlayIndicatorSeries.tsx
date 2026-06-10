import { useEffect, useRef } from 'react'
import type { ISeriesApi, LineData, UTCTimestamp } from 'lightweight-charts'
import { useChartContext } from '@/components/Chart/ChartContext'
import { useTheme } from '@/hooks/useTheme'
import type { IndicatorPoint } from '@/types/indicator'
import { OVERLAY_INDICATOR_COLORS } from '@/utils/indicatorDisplay'
import { resolveChartColor } from '@/utils/color'

interface OverlayIndicatorSeriesProps {
  seriesId: string
  label: string
  points: IndicatorPoint[]
  colorIndex: number
}

export function OverlayIndicatorSeries({
  seriesId,
  label,
  points,
  colorIndex,
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
      color,
      lineWidth: 2,
      title: label,
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
    seriesRef.current?.applyOptions({ color, title: label })
  }, [color, label])

  useEffect(() => {
    const series = seriesRef.current
    if (!series) {
      return
    }

    const data: LineData[] = points
      .filter((point) => point.value != null && Number.isFinite(point.value))
      .map((point) => ({
        time: point.time as UTCTimestamp,
        value: point.value as number,
      }))

    series.setData(data)
  }, [points])

  return null
}
