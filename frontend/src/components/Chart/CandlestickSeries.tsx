import { useEffect, useRef } from 'react'
import type { UTCTimestamp } from 'lightweight-charts'
import { useChartContext } from '@/components/Chart/ChartContext'
import type { OHLCVBar } from '@/types/candle'

interface CandlestickSeriesProps {
  candles: OHLCVBar[]
}

export function CandlestickSeries({ candles }: CandlestickSeriesProps) {
  const { chart, candleSeries } = useChartContext()
  const prevCountRef = useRef(0)

  useEffect(() => {
    if (!candleSeries || candles.length === 0) {
      if (candles.length === 0) {
        prevCountRef.current = 0
      }
      return
    }

    // Always setData (not update): scroll-back prepends require full sorted replacement.
    candleSeries.setData(
      candles.map((bar) => ({
        time: bar.time as UTCTimestamp,
        open: bar.open,
        high: bar.high,
        low: bar.low,
        close: bar.close,
      })),
    )

    const prevCount = prevCountRef.current
    const grewFromPrefetch = candles.length > prevCount && prevCount > 0
    prevCountRef.current = candles.length

    // fitContent only on first paint / timeframe switch — not after scroll-back prepend.
    // Re-fitting resets visible range to from≈0 and was retriggering prefetch loops.
    if (!grewFromPrefetch) {
      chart?.timeScale().fitContent()
    }
  }, [candleSeries, candles, chart])

  return null
}
