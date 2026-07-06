import { useEffect, useRef } from 'react'
import type { ISeriesApi, LineData } from 'lightweight-charts'
import { useChartContext } from '@/components/Chart/ChartContext'
import type { IndicatorPoint } from '@/types/indicator'
import { isFiniteNumber, toUtcTimestamp } from '@/utils/chartSeriesData'

interface ReplayOverlayIndicatorSeriesProps {
  seriesId: string
  label: string
  points: IndicatorPoint[]
  color: string
  lineWidth?: number
  visible?: boolean
}

export function ReplayOverlayIndicatorSeries({
  seriesId,
  label,
  points,
  color,
  lineWidth = 2,
  visible = true,
}: ReplayOverlayIndicatorSeriesProps) {
  const { chart } = useChartContext()
  const seriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const prevCountRef = useRef(0)

  useEffect(() => {
    if (!chart) {
      return
    }

    const series = chart.addLineSeries({
      lineWidth: (lineWidth ?? 2) as 1 | 2 | 3 | 4,
      priceLineVisible: false,
      lastValueVisible: true,
    })
    seriesRef.current = series

    return () => {
      chart.removeSeries(series)
      seriesRef.current = null
      prevCountRef.current = 0
    }
  }, [chart, seriesId])

  useEffect(() => {
    seriesRef.current?.applyOptions({
      color,
      title: label,
      visible,
      lineWidth: (lineWidth ?? 2) as 1 | 2 | 3 | 4,
    })
  }, [color, label, lineWidth, visible])

  useEffect(() => {
    const series = seriesRef.current
    if (!series) {
      return
    }

    const prevCount = prevCountRef.current
    if (points.length === 0) {
      series.setData([])
      prevCountRef.current = 0
      return
    }

    if (points.length === prevCount + 1 && prevCount > 0) {
      const point = points[points.length - 1]
      const time = toUtcTimestamp(point.time)
      if (time != null && isFiniteNumber(point.value)) {
        series.update({ time, value: point.value })
      }
    } else {
      const data: LineData[] = points.flatMap((point) => {
        const time = toUtcTimestamp(point.time)
        if (time == null || !isFiniteNumber(point.value)) {
          return []
        }
        return [{ time, value: point.value }]
      })
      series.setData(data)
    }

    prevCountRef.current = points.length
  }, [points, seriesId])

  return null
}
