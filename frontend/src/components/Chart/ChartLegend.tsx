import { useEffect, useMemo, useState } from 'react'
import type { MouseEventParams, UTCTimestamp } from 'lightweight-charts'
import { useChartContext } from '@/components/Chart/ChartContext'
import { useChartStore } from '@/stores/chartStore'
import type { OHLCVBar } from '@/types/candle'
import { formatChange, formatPrice, formatVolume } from '@/utils/format'
import { resolveChartColor } from '@/utils/color'
import type { Theme } from '@/types/theme'

interface ChartLegendProps {
  candles: OHLCVBar[]
  theme: Theme
}

function barFromCrosshair(
  param: MouseEventParams,
  candles: OHLCVBar[],
): OHLCVBar | null {
  if (!param.time) {
    return null
  }

  const time = param.time as UTCTimestamp
  return candles.find((bar) => bar.time === time) ?? null
}

export function ChartLegend({ candles, theme }: ChartLegendProps) {
  const { chart, candleSeries } = useChartContext()
  const symbol = useChartStore((state) => state.symbol)
  const timeframe = useChartStore((state) => state.timeframe)
  const [hoveredBar, setHoveredBar] = useState<OHLCVBar | null>(null)

  const activeBar = hoveredBar ?? candles[candles.length - 1] ?? null

  useEffect(() => {
    if (!chart) {
      return
    }

    const onCrosshairMove = (param: MouseEventParams) => {
      if (param.point === undefined || param.time === undefined) {
        setHoveredBar(null)
        return
      }

      const fromSeries = candleSeries
        ? (param.seriesData.get(candleSeries) as
            | { open: number; high: number; low: number; close: number }
            | undefined)
        : undefined

      if (fromSeries) {
        const match = barFromCrosshair(param, candles)
        if (match) {
          setHoveredBar(match)
          return
        }
      }

      setHoveredBar(barFromCrosshair(param, candles))
    }

    chart.subscribeCrosshairMove(onCrosshairMove)
    return () => chart.unsubscribeCrosshairMove(onCrosshairMove)
  }, [candleSeries, candles, chart])

  const change = useMemo(() => {
    if (!activeBar) {
      return null
    }
    return formatChange(activeBar.open, activeBar.close)
  }, [activeBar])

  if (!symbol || !activeBar || !change) {
    return null
  }

  const barColor = activeBar.close >= activeBar.open
    ? resolveChartColor('var(--color-bull)', theme)
    : resolveChartColor('var(--color-bear)', theme)

  const exchangeLabel = symbol.exchange
    ? symbol.exchange.charAt(0).toUpperCase() + symbol.exchange.slice(1)
    : ''

  return (
    <div className="pointer-events-none absolute left-3 top-3 z-20 flex flex-col gap-0.5 font-mono text-xs leading-tight">
      <div className="text-text-secondary">
        <span className="font-semibold text-text">{symbol.ticker}</span>
        <span className="text-text-secondary">
          {' '}
          · {timeframe}
          {exchangeLabel ? ` · ${exchangeLabel}` : ''}
        </span>
      </div>
      <div style={{ color: barColor }}>
        <span className="mr-2 text-text-secondary">O</span>
        {formatPrice(activeBar.open)}
        <span className="ml-2 mr-1 text-text-secondary">H</span>
        {formatPrice(activeBar.high)}
        <span className="ml-2 mr-1 text-text-secondary">L</span>
        {formatPrice(activeBar.low)}
        <span className="ml-2 mr-1 text-text-secondary">C</span>
        {formatPrice(activeBar.close)}
        <span className="ml-2">
          {change.delta} ({change.percent})
        </span>
      </div>
      <div style={{ color: barColor }}>
        <span className="text-text-secondary">Vol</span>
        <span className="mx-1 text-text-secondary">·</span>
        {formatVolume(activeBar.volume)}
      </div>
    </div>
  )
}
