import { useEffect, useRef } from 'react'
import { useChartContext } from '@/components/Chart/ChartContext'
import type { OHLCVBar } from '@/types/candle'
import { toUtcTimestamp } from '@/utils/chartSeriesData'
import { fitToVisibleBars } from '@/utils/chartViewport'

interface ReplayCandlestickSeriesProps {
  candles: OHLCVBar[]
  fitKey: string
  /** Bars rendered behind replay (ghost context) included in initial viewport fit. */
  leadingBarCount?: number
}

export function ReplayCandlestickSeries({
  candles,
  fitKey,
  leadingBarCount = 0,
}: ReplayCandlestickSeriesProps) {
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
      candles.length === prevCount + 1 && lastTime != null && lastTime > (prevLastTimeRef.current ?? -1)
    const sameLengthLastUpdated =
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

      const needsInitialFit = fittedKeyRef.current !== fitKey
      if (needsInitialFit && chart) {
        fitToVisibleBars(chart, leadingBarCount + candles.length)
        fittedKeyRef.current = fitKey
      }
    }

    prevCountRef.current = candles.length
    prevLastTimeRef.current = lastTime
  }, [candleSeries, candles, chart, fitKey, leadingBarCount])

  return null
}
