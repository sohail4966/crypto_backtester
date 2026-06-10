import { useEffect, useMemo, useState } from 'react'
import type { MouseEventParams, UTCTimestamp } from 'lightweight-charts'
import { useChartContext } from '@/components/Chart/ChartContext'
import { IndicatorTab } from '@/components/Indicators/IndicatorTab'
import { VisibilityToggle } from '@/components/Icons/VisibilityToggle'
import { useChartStore } from '@/stores/chartStore'
import { useIndicatorStore } from '@/stores/indicatorStore'
import type { ActiveIndicator, IndicatorSeriesMap } from '@/types/indicator'
import type { OHLCVBar } from '@/types/candle'
import { formatChange, formatPrice, formatVolume } from '@/utils/format'
import {
  indicatorValueAtTime,
  formatIndicatorValue,
  OVERLAY_INDICATOR_COLORS,
} from '@/utils/indicatorDisplay'
import { indicatorTabEntries } from '@/utils/indicatorCatalog'
import { resolveChartColor } from '@/utils/color'
import type { Theme } from '@/types/theme'

interface ChartLegendProps {
  candles: OHLCVBar[]
  theme: Theme
  overlayIndicators?: ActiveIndicator[]
  indicators?: IndicatorSeriesMap
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

export function ChartLegend({
  candles,
  theme,
  overlayIndicators = [],
  indicators = {},
}: ChartLegendProps) {
  const { chart, candleSeries } = useChartContext()
  const symbol = useChartStore((state) => state.symbol)
  const timeframe = useChartStore((state) => state.timeframe)
  const showVolume = useChartStore((state) => state.showVolume)
  const setShowVolume = useChartStore((state) => state.setShowVolume)
  const toggleVisible = useIndicatorStore((state) => state.toggleVisible)
  const openSettings = useIndicatorStore((state) => state.openSettings)
  const remove = useIndicatorStore((state) => state.remove)
  const [hoveredBar, setHoveredBar] = useState<OHLCVBar | null>(null)

  const activeBar = hoveredBar ?? candles[candles.length - 1] ?? null

  const overlayTabs = useMemo(
    () => indicatorTabEntries(overlayIndicators, 'overlay'),
    [overlayIndicators],
  )

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
    <div className="pointer-events-none absolute left-3 top-3 z-20 flex max-w-[calc(100%-1.5rem)] flex-col gap-1 font-mono text-xs leading-tight">
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

      <div className="pointer-events-auto flex flex-wrap items-center gap-1">
        <div
          className={`inline-flex items-center gap-1 rounded border border-border bg-surface/90 px-2 py-1 backdrop-blur-sm ${
            showVolume ? '' : 'opacity-60'
          }`}
          style={{ color: showVolume ? barColor : undefined }}
        >
          <span className={showVolume ? 'text-text' : 'text-text/50 line-through'}>
            Vol {formatVolume(activeBar.volume)}
          </span>
          <VisibilityToggle
            visible={showVolume}
            label="Volume"
            onToggle={() => setShowVolume(!showVolume)}
          />
        </div>

        {overlayTabs.map((tab, index) => {
          const item = overlayIndicators.find((row) => row.instanceId === tab.instanceId)
          const value =
            item && activeBar && tab.visible
              ? indicatorValueAtTime(indicators[item.seriesId] ?? [], activeBar.time)
              : null

          return (
            <IndicatorTab
              key={tab.instanceId}
              label={tab.label}
              value={value != null ? formatIndicatorValue(item!.key, value) : undefined}
              color={resolveChartColor(
                OVERLAY_INDICATOR_COLORS[index % OVERLAY_INDICATOR_COLORS.length],
                theme,
              )}
              visible={tab.visible}
              hasSettings={tab.hasSettings}
              onToggleVisible={() => toggleVisible(tab.instanceId)}
              onOpenSettings={
                tab.hasSettings ? () => openSettings(tab.instanceId) : undefined
              }
              onRemove={() => remove(tab.instanceId)}
              compact
            />
          )
        })}
      </div>
    </div>
  )
}
