import { useEffect, useRef } from 'react'
import type { IChartApi, ISeriesApi, MouseEventParams } from 'lightweight-charts'
import { useReplayStore } from '@/stores/replayStore'
import { fitToVisibleBars } from '@/utils/chartViewport'

interface UseReplayChartOptions {
  chart: IChartApi | null
  candleSeries: ISeriesApi<'Candlestick'> | null
  chartReady: boolean
  phase: string
  onAnchorClick: (barTime: number) => void
  /** Live candles used to resolve bar under click in pick_anchor. */
  liveCandles: { time: number }[]
}

/**
 * Anchor-click subscription, pan clamp to oldest revealed bar, follow-cursor.
 * Trail data is fed via ChartContainer selecting trailBars when authoritative.
 */
export function useReplayChart({
  chart,
  candleSeries,
  chartReady,
  phase,
  onAnchorClick,
  liveCandles,
}: UseReplayChartOptions): void {
  const followReplay = useReplayStore((s) => s.followReplay)
  const trailBars = useReplayStore((s) => s.trailBars)
  const trailAuthoritative = useReplayStore((s) => s.trailAuthoritative)
  const liveCandlesRef = useRef(liveCandles)
  liveCandlesRef.current = liveCandles
  const onAnchorClickRef = useRef(onAnchorClick)
  onAnchorClickRef.current = onAnchorClick

  // Anchor click in pick_anchor
  useEffect(() => {
    if (!chart || !chartReady || phase !== 'pick_anchor') {
      return
    }

    const handler = (param: MouseEventParams) => {
      if (useReplayStore.getState().phase !== 'pick_anchor') {
        return
      }
      let barTime: number | null = null
      if (param.time !== undefined) {
        barTime = Number(param.time)
      }
      if (barTime == null && param.point && candleSeries) {
        // Fallback: nearest live candle by crosshair time if available
        const candles = liveCandlesRef.current
        if (candles.length > 0 && param.time !== undefined) {
          barTime = Number(param.time)
        }
      }
      if (barTime == null || !Number.isFinite(barTime)) {
        return
      }
      // Prefer exact bar under click from live candles
      const exact = liveCandlesRef.current.find((c) => c.time === barTime)
      const resolved = exact?.time ?? barTime
      onAnchorClickRef.current(resolved)
    }

    chart.subscribeClick(handler)
    return () => {
      chart.unsubscribeClick(handler)
    }
  }, [chart, candleSeries, chartReady, phase])

  // Pan clamp: logical range min ≥ oldest revealed (no-op while trail empty)
  useEffect(() => {
    if (!chart || !chartReady || !trailAuthoritative) {
      return
    }

    const onRange = () => {
      const bars = useReplayStore.getState().trailBars
      if (bars.length === 0) {
        return
      }
      const range = chart.timeScale().getVisibleLogicalRange()
      if (!range) {
        return
      }
      if (range.from < 0) {
        const width = range.to - range.from
        chart.timeScale().setVisibleLogicalRange({
          from: 0,
          to: Math.max(width, 1),
        })
      }
    }

    chart.timeScale().subscribeVisibleLogicalRangeChange(onRange)
    return () => {
      chart.timeScale().unsubscribeVisibleLogicalRangeChange(onRange)
    }
  }, [chart, chartReady, trailAuthoritative])

  // Follow cursor — scroll so latest revealed stays in view
  useEffect(() => {
    if (!chart || !followReplay || !trailAuthoritative) {
      return
    }
    if (trailBars.length === 0) {
      return
    }
    fitToVisibleBars(chart, trailBars.length)
  }, [chart, followReplay, trailAuthoritative, trailBars.length, trailBars[trailBars.length - 1]?.time])
}
