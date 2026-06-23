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

    // Always setData (not update): scroll-back prepends require full sorted replacement.
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

    const prevCount = prevCountRef.current
    const grewFromPrefetch = candles.length > prevCount && prevCount > 0
    const shrankFromEviction = candles.length < prevCount && prevCount > 0
    prevCountRef.current = candles.length

    // fitContent once per symbol/timeframe — never on scroll eviction or prefetch prepend.
    const needsInitialFit = fittedKeyRef.current !== fitKey
    if (needsInitialFit && !grewFromPrefetch && !shrankFromEviction && chart) {
      fitToVisibleBars(chart, candles.length)
      fittedKeyRef.current = fitKey
    }
  }, [candleSeries, candles, chart, fitKey])

  return null
}
