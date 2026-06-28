import { useEffect, useMemo, useRef } from 'react'
import {
  ColorType,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type LineData,
  type SeriesType,
} from 'lightweight-charts'
import { IndicatorTab } from '@/components/Indicators/IndicatorTab'
import { subPaneGridOptions } from '@/components/Chart/chartOptions'
import { useChartContext } from '@/components/Chart/ChartContext'
import { useTheme } from '@/hooks/useTheme'
import { useChartStore } from '@/stores/chartStore'
import { useIndicatorStore } from '@/stores/indicatorStore'
import { type ActiveIndicator, type IndicatorPoint } from '@/types/indicator'
import {
  createIndicatorValueLookup,
  formatIndicatorValue,
  indicatorDisplayLabel,
  indicatorValueFromLookup,
  resolveIndicatorColor,
  colorIndexForInstance,
} from '@/utils/indicatorDisplay'
import { resolveChartColor } from '@/utils/color'
import { indicatorChipLabel } from '@/utils/indicatorCatalog'
import { isFiniteNumber, toUtcTimestamp } from '@/utils/chartSeriesData'

interface IndicatorSubPaneProps {
  paneId: string
  group: ActiveIndicator[]
  indicators: Record<string, IndicatorPoint[]>
  chartHeight: number
}

function toLineData(points: IndicatorPoint[]): LineData[] {
  return points.flatMap((point) => {
    const time = toUtcTimestamp(point.time)
    if (time == null || !isFiniteNumber(point.value)) {
      return []
    }
    return [{ time, value: point.value }]
  })
}

function primaryIndicator(group: ActiveIndicator[]): ActiveIndicator | undefined {
  const pool = group.filter((item) => item.visible !== false)
  const candidates = pool.length > 0 ? pool : group
  return (
    candidates.find((item) => item.key === 'MACD_LINE') ??
    candidates.find((item) => item.key !== 'MACD_HIST') ??
    candidates[0]
  )
}

export function IndicatorSubPane({
  paneId,
  group,
  indicators,
  chartHeight,
}: IndicatorSubPaneProps) {
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
  const indicatorLookupsRef = useRef<ReadonlyMap<string, ReadonlyMap<number, number>>>(new Map())
  const chartHeightRef = useRef(chartHeight)
  const onSubChartCrosshairMoveRef = useRef(onSubChartCrosshairMove)
  const { theme } = useTheme()
  const showGrid = useChartStore((state) => state.showGrid)
  const themeRef = useRef(theme)
  const showGridRef = useRef(showGrid)

  chartHeightRef.current = chartHeight
  onSubChartCrosshairMoveRef.current = onSubChartCrosshairMove
  themeRef.current = theme
  showGridRef.current = showGrid
  const toggleVisible = useIndicatorStore((state) => state.toggleVisible)
  const openSettings = useIndicatorStore((state) => state.openSettings)
  const remove = useIndicatorStore((state) => state.remove)

  const groupVisible = group.some((item) => item.visible !== false)

  groupRef.current = group
  const primary = primaryIndicator(group)
  const indicatorLookups = useMemo(() => {
    const bySeries = new Map<string, ReadonlyMap<number, number>>()
    for (const item of group) {
      bySeries.set(item.seriesId, createIndicatorValueLookup(indicators[item.seriesId] ?? []))
    }
    return bySeries
  }, [group, indicators])

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
      if (item.visible === false) {
        return []
      }
      const value = indicatorValueFromLookup(
        indicatorLookups.get(item.seriesId) ?? new Map(),
        activeTime,
      )
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
  }, [activeTime, group, indicatorLookups])

  useEffect(() => {
    indicatorLookupsRef.current = indicatorLookups
  }, [indicatorLookups])

  useEffect(() => {
    const container = containerRef.current
    if (!container) {
      return
    }

    const currentTheme = themeRef.current
    const accentColor = resolveChartColor('var(--color-accent)', currentTheme)
    const chart = createChart(container, {
      autoSize: false,
      width: container.clientWidth,
      height: chartHeightRef.current,
      layout: {
        background: {
          type: ColorType.Solid,
          color: resolveChartColor('var(--color-bg)', currentTheme),
        },
        textColor: resolveChartColor('var(--color-text-secondary)', currentTheme),
        attributionLogo: false,
      },
      grid: subPaneGridOptions(currentTheme, showGridRef.current),
      rightPriceScale: {
        borderColor: resolveChartColor('var(--color-border)', currentTheme),
      },
      timeScale: {
        visible: false,
        borderColor: resolveChartColor('var(--color-border)', currentTheme),
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
    const seriesMap = seriesRef.current

    const onCrosshairMove = (param: Parameters<typeof onSubChartCrosshairMove>[0]) => {
      onSubChartCrosshairMoveRef.current(param)
    }

    const observer = new ResizeObserver(() => {
      if (!chartRef.current || !containerRef.current) {
        return
      }
      const { width } = containerRef.current.getBoundingClientRect()
      chartRef.current.applyOptions({
        width: Math.max(1, Math.floor(width)),
        height: chartHeightRef.current,
      })
    })
    observer.observe(container)

    chart.subscribeCrosshairMove(onCrosshairMove)

    return () => {
      chart.unsubscribeCrosshairMove(onCrosshairMove)
      observer.disconnect()
      seriesMap.clear()
      chart.remove()
      chartRef.current = null
    }
  }, [paneId])

  useEffect(() => {
    const chart = chartRef.current
    if (!chart) {
      return
    }
    const accentColor = resolveChartColor('var(--color-accent)', theme)
    chart.applyOptions({
      layout: {
        background: { type: ColorType.Solid, color: resolveChartColor('var(--color-bg)', theme) },
        textColor: resolveChartColor('var(--color-text-secondary)', theme),
      },
      grid: subPaneGridOptions(theme, showGrid),
      rightPriceScale: {
        borderColor: resolveChartColor('var(--color-border)', theme),
      },
      timeScale: {
        borderColor: resolveChartColor('var(--color-border)', theme),
      },
      crosshair: {
        vertLine: {
          visible: true,
          labelVisible: false,
          color: accentColor,
        },
        horzLine: { visible: false },
      },
    })
  }, [showGrid, theme])

  useEffect(() => {
    const chart = chartRef.current
    const container = containerRef.current
    if (!chart || !container) {
      return
    }
    const { width } = container.getBoundingClientRect()
    chart.applyOptions({
      width: Math.max(1, Math.floor(width)),
      height: chartHeight,
    })
  }, [chartHeight])

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
        return indicatorValueFromLookup(
          indicatorLookupsRef.current.get(item.seriesId) ?? new Map(),
          time,
        )
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

    const activeSeriesIds = new Set(group.map((item) => item.seriesId))
    for (const [seriesId, series] of seriesRef.current.entries()) {
      if (!activeSeriesIds.has(seriesId)) {
        chart.removeSeries(series)
        seriesRef.current.delete(seriesId)
      }
    }

    for (const item of group) {
      const points = indicators[item.seriesId] ?? []
      const isHist = item.key === 'MACD_HIST'
      const seriesColor = resolveIndicatorColor(
        item,
        colorIndexForInstance(group, item.instanceId),
        theme,
      )

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
            color: seriesColor,
            lineWidth: item.lineWidth ?? 2,
            title: item.key,
            priceLineVisible: false,
            lastValueVisible: true,
          })
        }
        seriesRef.current.set(item.seriesId, series)
      }

      if (isHist) {
        const bear = resolveChartColor('var(--color-bear)', theme)
        series.setData(
          points.flatMap((point) => {
            const time = toUtcTimestamp(point.time)
            if (time == null || !isFiniteNumber(point.value)) {
              return []
            }
            return [{
              time,
              value: point.value,
              color: point.value >= 0 ? seriesColor : bear,
            }]
          }),
        )
      } else {
        series.setData(toLineData(points))
        series.applyOptions({ color: seriesColor, lineWidth: item.lineWidth ?? 2 })
      }

      series.applyOptions({ visible: item.visible !== false })
    }
  }, [group, indicators, theme])

  const tabLabel = indicatorChipLabel(group[0]?.key ?? 'Indicator', group[0]?.params ?? {})
  const tabValue =
    groupVisible && valueRows.length > 0
      ? valueRows.map((row) => row.value).join(' · ')
      : undefined
  const hasSettings = true
  const instanceId = group[0]?.instanceId
  const tabColor = primary
    ? resolveIndicatorColor(primary, colorIndexForInstance(group, primary.instanceId), theme)
    : undefined

  return (
    <div className={`shrink-0 bg-bg ${groupVisible ? '' : 'opacity-60'}`}>
      <div className="pointer-events-auto px-3 py-1">
        <IndicatorTab
          label={tabLabel}
          value={tabValue}
          color={tabColor}
          visible={groupVisible}
          hasSettings={hasSettings}
          onToggleVisible={() => {
            if (instanceId) {
              toggleVisible(instanceId)
            }
          }}
          onOpenSettings={instanceId ? () => openSettings(instanceId) : undefined}
          onRemove={instanceId ? () => remove(instanceId) : undefined}
          compact
        />
      </div>
      <div
        ref={containerRef}
        className={groupVisible ? '' : 'overflow-hidden'}
        style={{ height: groupVisible ? chartHeight : 0 }}
      />
    </div>
  )
}
