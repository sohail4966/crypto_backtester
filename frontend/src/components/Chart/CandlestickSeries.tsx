import { useEffect, useRef } from 'react'
import { useChartContext } from '@/components/Chart/ChartContext'
import type { OHLCVBar } from '@/types/candle'
import { toUtcTimestamp } from '@/utils/chartSeriesData'
import { fitToVisibleBars } from '@/utils/chartViewport'

interface CandlestickSeriesProps {
  candles: OHLCVBar[]
  /** Changes on symbol/timeframe switch to trigger a single fitContent. */
  fitKey: string
}

export function CandlestickSeries({ candles, fitKey }: CandlestickSeriesProps) {
  const { chart, candleSeries } = useChartContext()
  const fittedKeyRef = useRef<string | null>(null)
  const prevCountRef = useRef(0)

  useEffect(() => {
    fittedKeyRef.current = null
    prevCountRef.current = 0
  }, [fitKey])

  useEffect(() => {
    return () => {
      candleSeries?.setData([])
    }
  }, [candleSeries])

  useEffect(() => {
    if (!candleSeries) {
      return
    }

    if (candles.length === 0) {
      candleSeries.setData([])
      prevCountRef.current = 0
      return
    }

    const prevCount = prevCountRef.current
    candleSeries.setData(
      candles.flatMap((bar) => {
        const time = toUtcTimestamp(bar.time)
        return time == null
          ? []
          : [{
              time,
              open: bar.open,
              high: bar.high,
              low: bar.low,
              close: bar.close,
            }]
      }),
    )

    const grewFromPrefetch = candles.length > prevCount && prevCount > 0
    const shrankFromEviction = candles.length < prevCount && prevCount > 0

    if (
      fittedKeyRef.current !== fitKey &&
      !grewFromPrefetch &&
      !shrankFromEviction &&
      chart
    ) {
      fitToVisibleBars(chart, candles.length)
      fittedKeyRef.current = fitKey
    }

    prevCountRef.current = candles.length
  }, [candleSeries, candles, chart, fitKey])

  return null
}
