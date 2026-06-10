import { useEffect, useMemo, useRef } from 'react'
import {
  ColorType,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type LineData,
  type SeriesType,
  type UTCTimestamp,
} from 'lightweight-charts'
import { useChartContext } from '@/components/Chart/ChartContext'
import { useTheme } from '@/hooks/useTheme'
import { isMacdKey, type ActiveIndicator, type IndicatorPoint } from '@/types/indicator'
import {
  formatIndicatorValue,
  indicatorDisplayLabel,
  indicatorValueAtTime,
} from '@/utils/indicatorDisplay'
import { resolveChartColor } from '@/utils/color'

const SUBCHART_HEIGHT = 112

interface IndicatorSubPaneProps {
  paneId: string
  group: ActiveIndicator[]
  indicators: Record<string, IndicatorPoint[]>
}

function toLineData(points: IndicatorPoint[]): LineData[] {
  return points
    .filter((point) => point.value != null && Number.isFinite(point.value))
    .map((point) => ({
      time: point.time as UTCTimestamp,
      value: point.value as number,
    }))
}

function primaryIndicator(group: ActiveIndicator[]): ActiveIndicator | undefined {
  return (
    group.find((item) => item.key === 'MACD_LINE') ??
    group.find((item) => item.key !== 'MACD_HIST') ??
    group[0]
  )
}

export function IndicatorSubPane({ paneId, group, indicators }: IndicatorSubPaneProps) {
  const {
    chart: mainChart,
    crosshairTime,
    registerSubChart,
    unregisterSubChart,
    onSubChartCrosshairMove,
  } = useChartContext()
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<Map<string, ISeriesApi<'Line' | 'Histogram'>>>(new Map())
  const groupRef = useRef(group)
  const indicatorsRef = useRef(indicators)
  const { theme } = useTheme()

  groupRef.current = group
  indicatorsRef.current = indicators

  const primary = primaryIndicator(group)

  const title = group.some((item) => isMacdKey(item.key))
    ? 'MACD'
    : indicatorDisplayLabel(group[0]?.key ?? 'Indicator', group[0]?.params ?? {})

  const latestTime = useMemo(() => {
    for (const item of group) {
      const last = indicators[item.seriesId]?.at(-1)
      if (last) {
        return last.time
      }
    }
    return null
  }, [group, indicators])

  const activeTime = crosshairTime ?? latestTime

  const valueRows = useMemo(() => {
    if (activeTime == null) {
      return []
    }
    return group.flatMap((item) => {
      const value = indicatorValueAtTime(indicators[item.seriesId] ?? [], activeTime)
      if (value == null) {
        return []
      }
      return [
        {
          key: item.seriesId,
          label: indicatorDisplayLabel(item.key, item.params),
          value: formatIndicatorValue(item.key, value),
        },
      ]
    })
  }, [activeTime, group, indicators])

  useEffect(() => {
    const container = containerRef.current
    if (!container) {
      return
    }

    const accentColor = resolveChartColor('var(--color-accent)', theme)
    const chart = createChart(container, {
      autoSize: false,
      width: container.clientWidth,
      height: SUBCHART_HEIGHT,
      layout: {
        background: { type: ColorType.Solid, color: resolveChartColor('var(--color-bg)', theme) },
        textColor: resolveChartColor('var(--color-text-secondary)', theme),
        attributionLogo: false,
      },
      grid: {
        vertLines: { visible: false },
        horzLines: { color: resolveChartColor('var(--color-border)', theme) },
      },
      rightPriceScale: {
        borderColor: resolveChartColor('var(--color-border)', theme),
      },
      timeScale: {
        visible: false,
        borderColor: resolveChartColor('var(--color-border)', theme),
      },
      handleScroll: false,
      handleScale: false,
      crosshair: {
        vertLine: {
          visible: true,
          labelVisible: false,
          color: accentColor,
        },
        horzLine: { visible: false },
      },
    })

    chartRef.current = chart

    const observer = new ResizeObserver(() => {
      if (!chartRef.current || !containerRef.current) {
        return
      }
      const { width } = containerRef.current.getBoundingClientRect()
      chartRef.current.applyOptions({
        width: Math.max(1, Math.floor(width)),
        height: SUBCHART_HEIGHT,
      })
    })
    observer.observe(container)

    chart.subscribeCrosshairMove(onSubChartCrosshairMove)

    return () => {
      chart.unsubscribeCrosshairMove(onSubChartCrosshairMove)
      observer.disconnect()
      seriesRef.current.clear()
      chart.remove()
      chartRef.current = null
    }
  }, [onSubChartCrosshairMove, theme])

  useEffect(() => {
    const chart = chartRef.current
    if (!chart) {
      return
    }

    const accentColor = resolveChartColor('var(--color-accent)', theme)
    chart.applyOptions({
      crosshair: {
        vertLine: {
          visible: true,
          labelVisible: false,
          color: accentColor,
        },
        horzLine: { visible: false },
      },
    })
  }, [theme])

  useEffect(() => {
    const chart = chartRef.current
    if (!chart) {
      return
    }

    registerSubChart(paneId, {
      chart,
      getPrimarySeries: () => {
        const item = primaryIndicator(groupRef.current)
        return item ? (seriesRef.current.get(item.seriesId) as ISeriesApi<SeriesType> | null) : null
      },
      getPriceAtTime: (time: number) => {
        const item = primaryIndicator(groupRef.current)
        if (!item) {
          return null
        }
        return indicatorValueAtTime(indicatorsRef.current[item.seriesId] ?? [], time)
      },
    })

    return () => unregisterSubChart(paneId)
  }, [paneId, primary?.seriesId, registerSubChart, unregisterSubChart])

  useEffect(() => {
    const subChart = chartRef.current
    if (!subChart || !mainChart) {
      return
    }

    const syncFromMain = () => {
      const range = mainChart.timeScale().getVisibleLogicalRange()
      if (range) {
        subChart.timeScale().setVisibleLogicalRange(range)
      }
    }

    syncFromMain()
    mainChart.timeScale().subscribeVisibleLogicalRangeChange(syncFromMain)
    return () => mainChart.timeScale().unsubscribeVisibleLogicalRangeChange(syncFromMain)
  }, [mainChart])

  useEffect(() => {
    const chart = chartRef.current
    if (!chart) {
      return
    }

    for (const item of group) {
      const points = indicators[item.seriesId] ?? []
      const isHist = item.key === 'MACD_HIST'

      let series = seriesRef.current.get(item.seriesId)
      if (!series) {
        if (isHist) {
          series = chart.addHistogramSeries({
            priceFormat: { type: 'price', precision: 4, minMove: 0.0001 },
            priceLineVisible: false,
            lastValueVisible: false,
          })
        } else {
          series = chart.addLineSeries({
            color: resolveChartColor(
              item.key === 'MACD_SIGNAL' ? '#f59e0b' : 'var(--color-accent)',
              theme,
            ),
            lineWidth: 2,
            title: item.key,
            priceLineVisible: false,
            lastValueVisible: true,
          })
        }
        seriesRef.current.set(item.seriesId, series)
      }

      if (isHist) {
        const bull = resolveChartColor('var(--color-bull)', theme)
        const bear = resolveChartColor('var(--color-bear)', theme)
        series.setData(
          points
            .filter((point) => point.value != null && Number.isFinite(point.value))
            .map((point) => ({
              time: point.time as UTCTimestamp,
              value: point.value as number,
              color: (point.value as number) >= 0 ? bull : bear,
            })),
        )
      } else {
        series.setData(toLineData(points))
      }
    }
  }, [group, indicators, theme])

  return (
    <div className="shrink-0 border-t border-border bg-bg">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 px-3 py-1 font-mono text-[10px] leading-tight">
        <span className="font-semibold uppercase tracking-wider text-text-secondary">
          {title}
        </span>
        {valueRows.map((row) => (
          <span key={row.key} className="text-text">
            {group.length > 1 || isMacdKey(group[0]?.key ?? '') ? (
              <>
                <span className="text-text-secondary">{row.label}</span>
                <span className="mx-1 text-text-secondary">·</span>
              </>
            ) : null}
            {row.value}
          </span>
        ))}
      </div>
      <div ref={containerRef} style={{ height: SUBCHART_HEIGHT }} />
    </div>
  )
}
