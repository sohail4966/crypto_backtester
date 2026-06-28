import { useEffect, useRef } from 'react'
import type { ISeriesApi, LineData } from 'lightweight-charts'
import { useChartContext } from '@/components/Chart/ChartContext'
import type { IndicatorPoint } from '@/types/indicator'
import { isFiniteNumber, toUtcTimestamp } from '@/utils/chartSeriesData'

interface OverlayIndicatorSeriesProps {
  seriesId: string
  label: string
  points: IndicatorPoint[]
  color: string
  lineWidth?: number
  visible?: boolean
}

export function OverlayIndicatorSeries({
  seriesId,
  label,
  points,
  color,
  lineWidth = 2,
  visible = true,
}: OverlayIndicatorSeriesProps) {
  const { chart } = useChartContext()
  const seriesRef = useRef<ISeriesApi<'Line'> | null>(null)

  useEffect(() => {
    if (!chart) {
      return
    }

    const series = chart.addLineSeries({
      lineWidth,
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
    seriesRef.current?.applyOptions({ color, title: label, visible, lineWidth })
  }, [color, label, lineWidth, visible])

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
  }, [points, seriesId])

  return null
}
