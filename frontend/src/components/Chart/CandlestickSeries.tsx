import { useEffect, useRef } from 'react'
import { useChartContext } from '@/components/Chart/ChartContext'
import type { OHLCVBar } from '@/types/candle'
import { toUtcTimestamp } from '@/utils/chartSeriesData'
import {
  captureVisibleTimeRange,
  fitToVisibleBars,
  restoreVisibleTimeRange,
} from '@/utils/chartViewport'

interface CandlestickSeriesProps {
  candles: OHLCVBar[]
  /** Changes on symbol/timeframe switch to trigger a single fitContent. */
  fitKey: string
  /** Keep the current time window when candle data changes (replay). */
  lockViewport?: boolean
  /** Append one bar via series.update instead of setData (replay ticks). */
  incrementalAppend?: boolean
}

export function CandlestickSeries({
  candles,
  fitKey,
  lockViewport = false,
  incrementalAppend = false,
}: CandlestickSeriesProps) {
  const { chart, candleSeries } = useChartContext()
  const fittedKeyRef = useRef<string | null>(null)
  const prevCountRef = useRef(0)
  const prevLastTimeRef = useRef<number | null>(null)

  useEffect(() => {
    fittedKeyRef.current = null
    prevCountRef.current = 0
    prevLastTimeRef.current = null
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
      prevLastTimeRef.current = null
      return
    }

    const lastBar = candles[candles.length - 1]
    const lastTime = lastBar?.time ?? null
    const prevCount = prevCountRef.current
    const grewByOne =
      incrementalAppend &&
      candles.length === prevCount + 1 &&
      lastTime != null &&
      lastTime > (prevLastTimeRef.current ?? -1)
    const sameLengthLastUpdated =
      incrementalAppend &&
      candles.length === prevCount &&
      prevCount > 0 &&
      lastTime != null &&
      lastTime === prevLastTimeRef.current

    if (grewByOne || sameLengthLastUpdated) {
      const time = toUtcTimestamp(lastBar.time)
      if (time != null) {
        candleSeries.update({
          time,
          open: lastBar.open,
          high: lastBar.high,
          low: lastBar.low,
          close: lastBar.close,
        })
      }
    } else {
      const visibleRange = lockViewport ? captureVisibleTimeRange(chart) : null
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
      restoreVisibleTimeRange(chart, visibleRange)

      const grewFromPrefetch = candles.length > prevCount && prevCount > 0
      const shrankFromEviction = candles.length < prevCount && prevCount > 0

      if (
        !lockViewport &&
        fittedKeyRef.current !== fitKey &&
        !grewFromPrefetch &&
        !shrankFromEviction &&
        chart
      ) {
        fitToVisibleBars(chart, candles.length)
        fittedKeyRef.current = fitKey
      }
    }

    prevCountRef.current = candles.length
    prevLastTimeRef.current = lastTime
  }, [candleSeries, candles, chart, fitKey, incrementalAppend, lockViewport])

  return null
}
