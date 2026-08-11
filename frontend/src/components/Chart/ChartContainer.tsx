import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import {
  createChart,
  type IChartApi,
  type ISeriesApi,
  type LogicalRange,
  type MouseEventParams,
  type UTCTimestamp,
} from 'lightweight-charts'
import { CandlestickSeries } from '@/components/Chart/CandlestickSeries'
import { ChartContext, type SubChartHandle } from '@/components/Chart/ChartContext'
import { ChartLegend } from '@/components/Chart/ChartLegend'
import { DrawingsLayer } from '@/components/Drawings/DrawingsLayer'
import { OverlayIndicatorSeries } from '@/components/Indicators/OverlayIndicatorSeries'
import { IndicatorSubPane } from '@/components/Indicators/IndicatorSubPane'
import { ChartZoomControls } from '@/components/Chart/ChartZoomControls'
import { VolumeSeries } from '@/components/Chart/VolumeSeries'
import { useOptionalReplaySession } from '@/components/Replay/ReplaySessionContext'
import { useTheme } from '@/hooks/useTheme'
import { useDrawingInteraction } from '@/hooks/useDrawingInteraction'
import { useDrawingKeyboard } from '@/hooks/useDrawingKeyboard'
import { useMultiChartSync } from '@/hooks/useMultiChartSync'
import { useChartStore } from '@/stores/chartStore'
import { useIndicatorStore } from '@/stores/indicatorStore'
import { useReplayStore } from '@/stores/replayStore'
import { publishSync } from '@/stores/syncStore'
import { useWorkspaceStore } from '@/stores/workspaceStore'
import type { ActiveIndicator, IndicatorSpec } from '@/types/indicator'
import type { ChartTimeframe } from '@/constants/chart'
import type { Symbol } from '@/types/symbol'
import { useChunkManager } from '@/hooks/useChunkManager'
import { usePaneLayout } from '@/hooks/usePaneLayout'
import { useReplayChart } from '@/hooks/useReplayChart'
import type { ChartTimezoneId } from '@/constants/timezone'
import { PaneResizeHandle } from '@/components/Chart/PaneResizeHandle'
import type { Theme } from '@/types/theme'
import { chartOptions, measureChartArea, seriesColors } from '@/components/Chart/chartOptions'
import {
  loadChartTimezonePreference,
} from '@/utils/chartTimezone'
import {
  colorIndexForInstance,
  indicatorDisplayLabel,
  resolveIndicatorColor,
} from '@/utils/indicatorDisplay'
import {
  candleCloseFromLookup,
  createCandleCloseLookup,
  safeSetCrosshairPosition,
} from '@/utils/crosshairSync'

interface ChartContainerProps {
  paneId?: string
  className?: string
  isActive?: boolean
  symbolOverride?: Symbol | null
  timeframeOverride?: ChartTimeframe
  onActivate?: () => void
}

export function ChartContainer({
  paneId = 'main',
  className,
  isActive = true,
  symbolOverride,
  timeframeOverride,
  onActivate,
}: ChartContainerProps) {
  const layoutRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null)
  const onRangeChangeRef = useRef<(range: LogicalRange | null) => void>(() => {})
  const themeRef = useRef<Theme>('dark')
  const timezoneRef = useRef<ChartTimezoneId>(loadChartTimezonePreference())
  const showGridRef = useRef(useChartStore.getState().showGrid)
  const subChartsRef = useRef(new Map<string, SubChartHandle>())
  const syncingCrosshairRef = useRef(false)
  const candleCloseLookupRef = useRef<ReadonlyMap<number, number>>(new Map())

  const { theme } = useTheme()
  const storeSymbol = useChartStore((state) => state.symbol)
  const storeTimeframe = useChartStore((state) => state.timeframe)
  const symbol = symbolOverride !== undefined ? symbolOverride : storeSymbol
  const timeframe =
    timeframeOverride !== undefined ? timeframeOverride : storeTimeframe
  const timezone = useChartStore((state) => state.timezone)
  const showGrid = useChartStore((state) => state.showGrid)
  const pulseZoomControls = useChartStore((state) => state.pulseZoomControls)
  const activeIndicators = useIndicatorStore((state) => state.active)
  const trailAuthoritative = useReplayStore((state) => state.trailAuthoritative)
  const trailBars = useReplayStore((state) => state.trailBars)
  const trailIndicators = useReplayStore((state) => state.trailIndicators)
  const replayPhase = useReplayStore((state) => state.phase)
  const replaySessionId = useReplayStore((state) => state.sessionId)
  const replaySession = useOptionalReplaySession()
  const useReplayTrail = Boolean(isActive && trailAuthoritative)

  const indicatorSpecs = useMemo((): IndicatorSpec[] => {
    const seen = new Set<string>()
    const specs: IndicatorSpec[] = []
    for (const item of activeIndicators) {
      if (item.visible === false) {
        continue
      }
      const id = `${item.key}:${JSON.stringify(item.params)}:${item.pane}`
      if (seen.has(id)) {
        continue
      }
      seen.add(id)
      specs.push({ key: item.key, params: item.params, pane: item.pane })
    }
    return specs
  }, [activeIndicators])

  const overlayIndicators = useMemo(
    () => activeIndicators.filter((item) => item.pane === 'overlay'),
    [activeIndicators],
  )

  const subchartGroups = useMemo((): ActiveIndicator[][] => {
    const groups = new Map<string, ActiveIndicator[]>()
    for (const item of activeIndicators) {
      if (item.pane !== 'subchart') {
        continue
      }
      const list = groups.get(item.groupInstanceId) ?? []
      list.push(item)
      groups.set(item.groupInstanceId, list)
    }
    return [...groups.values()]
  }, [activeIndicators])

  const symbolId = symbol?.id
  const fitKey = useReplayTrail
    ? `replay-${replaySessionId ?? 'none'}`
    : `${symbolId ?? 'none'}-${timeframe}`

  const {
    candles: liveCandles,
    indicators: liveIndicators,
    status,
    error,
    onVisibleRangeChange,
  } = useChunkManager(symbolId, timeframe, indicatorSpecs)

  const candles = useReplayTrail ? trailBars : liveCandles
  const indicators = useReplayTrail ? trailIndicators : liveIndicators

  const candleCloseLookup = useMemo(
    () => createCandleCloseLookup(candles),
    [candles],
  )

  const [chartReady, setChartReady] = useState(false)
  const [crosshairTime, setCrosshairTime] = useState<number | null>(null)
  const [layoutHeight, setLayoutHeight] = useState(0)

  const {
    mainPaneHeight,
    groupKeys,
    getSubChartHeight,
    onResizeAboveSub,
    onResizeBetweenSubs,
  } = usePaneLayout(layoutHeight, subchartGroups)

  useReplayChart({
    chart: isActive && chartReady ? chartRef.current : null,
    candleSeries: isActive && chartReady ? candleSeriesRef.current : null,
    chartReady: isActive && chartReady,
    phase: isActive ? replayPhase : 'inactive',
    liveCandles,
    onAnchorClick: (barTime) => {
      void replaySession?.startFromAnchor(barTime)
    },
  })

  useDrawingKeyboard(isActive)
  useDrawingInteraction({
    chart: isActive && chartReady ? chartRef.current : null,
    candleSeries: isActive && chartReady ? candleSeriesRef.current : null,
    chartReady: isActive && chartReady,
  })

  const multiSync = useMultiChartSync({
    paneId,
    chart: chartReady ? chartRef.current : null,
    candleSeries: chartReady ? candleSeriesRef.current : null,
    chartReady,
    candleCloseLookup,
  })
  const multiSyncRef = useRef(multiSync)
  multiSyncRef.current = multiSync

  useEffect(() => {
    candleCloseLookupRef.current = candleCloseLookup
  }, [candleCloseLookup])

  useEffect(() => {
    const layout = layoutRef.current
    if (!layout) {
      return
    }

    const observer = new ResizeObserver(() => {
      setLayoutHeight(Math.floor(layout.clientHeight))
    })
    observer.observe(layout)
    setLayoutHeight(Math.floor(layout.clientHeight))
    return () => observer.disconnect()
  }, [])

  const registerSubChart = useCallback((id: string, handle: SubChartHandle) => {
    subChartsRef.current.set(id, handle)
  }, [])

  const unregisterSubChart = useCallback((id: string) => {
    subChartsRef.current.delete(id)
  }, [])

  const applyCrosshairTime = useCallback((time: UTCTimestamp | null) => {
    if (syncingCrosshairRef.current) {
      return
    }

    syncingCrosshairRef.current = true
    try {
      setCrosshairTime(time)
      const main = chartRef.current
      if (!main) {
        return
      }

      if (time == null) {
        main.clearCrosshairPosition()
        subChartsRef.current.forEach((handle) => handle.chart.clearCrosshairPosition())
        return
      }

      const candleSeries = candleSeriesRef.current
      if (candleSeries) {
        const close = candleCloseFromLookup(candleCloseLookupRef.current, time)
        if (close != null) {
          safeSetCrosshairPosition(main, close, time, candleSeries)
        }
      }

      subChartsRef.current.forEach((handle) => {
        const series = handle.getPrimarySeries()
        const price = handle.getPriceAtTime(time)
        if (series && price != null) {
          safeSetCrosshairPosition(handle.chart, price, time, series)
        }
      })
    } finally {
      syncingCrosshairRef.current = false
    }

    if (!multiSyncRef.current.isApplying()) {
      const sync = useWorkspaceStore.getState().sync
      if (sync.crosshair) {
        publishSync({
          type: 'crosshair',
          sourcePaneId: paneId,
          time: time == null ? null : Number(time),
        })
      }
    }
  }, [paneId])

  const onSubChartCrosshairMove = useCallback(
    (param: MouseEventParams) => {
      if (syncingCrosshairRef.current) {
        return
      }
      if (param.point === undefined || param.time === undefined) {
        return
      }
      applyCrosshairTime(param.time as UTCTimestamp)
    },
    [applyCrosshairTime],
  )

  const clearCrosshair = useCallback(() => {
    applyCrosshairTime(null)
  }, [applyCrosshairTime])

  useEffect(() => {
    themeRef.current = theme
  }, [theme])

  useEffect(() => {
    timezoneRef.current = timezone
  }, [timezone])

  useEffect(() => {
    showGridRef.current = showGrid
  }, [showGrid])

  useEffect(() => {
    onRangeChangeRef.current = useReplayTrail
      ? () => {}
      : onVisibleRangeChange
  }, [onVisibleRangeChange, useReplayTrail])

  useEffect(() => {
    const main = chartRef.current
    if (!main || !chartReady) {
      return
    }

    const onMainCrosshairMove = (param: MouseEventParams) => {
      if (syncingCrosshairRef.current) {
        return
      }
      if (param.point === undefined || param.time === undefined) {
        return
      }
      applyCrosshairTime(param.time as UTCTimestamp)
    }

    main.subscribeCrosshairMove(onMainCrosshairMove)
    return () => main.unsubscribeCrosshairMove(onMainCrosshairMove)
  }, [applyCrosshairTime, chartReady])

  useEffect(() => {
    const container = containerRef.current
    if (!container || !chartReady) {
      return
    }

    const onWheel = () => {
      pulseZoomControls()
    }

    container.addEventListener('wheel', onWheel, { passive: true })
    return () => container.removeEventListener('wheel', onWheel)
  }, [chartReady, pulseZoomControls])

  useEffect(() => {
    const container = containerRef.current
    if (!container) {
      return
    }

    const { width, height } = measureChartArea(container)
    const chart = createChart(container, {
      ...chartOptions(themeRef.current, showGridRef.current, timezoneRef.current),
      width,
      height,
    })

    const candleSeries = chart.addCandlestickSeries(seriesColors(themeRef.current))
    const volumeSeries = chart.addHistogramSeries({
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    })

    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    })

    const onVisibleLogicalRangeChange = (range: LogicalRange | null) => {
      onRangeChangeRef.current(range)
      if (multiSyncRef.current.isApplying()) {
        return
      }
      const sync = useWorkspaceStore.getState().sync
      if (!sync.visibleRange) {
        return
      }
      publishSync({
        type: 'visibleRange',
        sourcePaneId: paneId,
        range: range ? { from: range.from, to: range.to } : null,
      })
    }
    chart.timeScale().subscribeVisibleLogicalRangeChange(onVisibleLogicalRangeChange)

    chartRef.current = chart
    candleSeriesRef.current = candleSeries
    volumeSeriesRef.current = volumeSeries
    setChartReady(true)

    const observer = new ResizeObserver(() => {
      if (!chartRef.current || !containerRef.current) {
        return
      }
      const next = measureChartArea(containerRef.current)
      chartRef.current.applyOptions(next)
    })
    observer.observe(container)

    return () => {
      observer.disconnect()
      chart.timeScale().unsubscribeVisibleLogicalRangeChange(onVisibleLogicalRangeChange)
      chart.remove()
      chartRef.current = null
      candleSeriesRef.current = null
      volumeSeriesRef.current = null
      setChartReady(false)
    }
  }, [paneId])

  useEffect(() => {
    const container = containerRef.current
    const chart = chartRef.current
    if (!container || !chart || !chartReady) {
      return
    }
    chart.applyOptions(measureChartArea(container, mainPaneHeight))
  }, [chartReady, mainPaneHeight])

  useEffect(() => {
    const chart = chartRef.current
    if (!chart || !chartReady) {
      return
    }
    chart.applyOptions(chartOptions(theme, showGrid, timezone))
    candleSeriesRef.current?.applyOptions(seriesColors(theme))
  }, [showGrid, theme, timezone, chartReady])

  const contextValue = useMemo(
    () => ({
      chart: chartReady ? chartRef.current : null,
      candleSeries: chartReady ? candleSeriesRef.current : null,
      volumeSeries: chartReady ? volumeSeriesRef.current : null,
      crosshairTime,
      registerSubChart,
      unregisterSubChart,
      onSubChartCrosshairMove,
    }),
    [
      chartReady,
      crosshairTime,
      onSubChartCrosshairMove,
      registerSubChart,
      unregisterSubChart,
    ],
  )

  let overlay: ReactNode = null
  if (!symbol) {
    overlay = (
      <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center bg-bg/80 text-sm text-text-secondary">
        Select a symbol to load the chart.
      </div>
    )
  } else if (!useReplayTrail && (status === 'loading' || status === 'idle')) {
    overlay = (
      <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center bg-bg/80 text-sm text-text-secondary">
        Loading chart…
      </div>
    )
  } else if (!useReplayTrail && status === 'error') {
    overlay = (
      <div className="absolute inset-0 z-10 flex items-center justify-center bg-bg/90 px-6 text-center text-sm text-bear">
        {error?.message ?? 'Failed to load chart data.'}
      </div>
    )
  } else if (!useReplayTrail && candles.length === 0) {
    overlay = (
      <div className="absolute inset-0 z-10 flex items-center justify-center bg-bg/90 px-6 text-center text-sm text-text-secondary">
        No candle data returned for this symbol and timeframe.
      </div>
    )
  }

  const showSeries = chartReady && (useReplayTrail || candles.length > 0)

  return (
    <ChartContext.Provider value={contextValue}>
      <div
        ref={layoutRef}
        className={`${className ?? 'relative flex h-full min-h-[420px] w-full flex-col'} overflow-hidden`}
        onMouseLeave={clearCrosshair}
        onMouseDown={() => onActivate?.()}
      >
        <div
          className="relative min-h-0 shrink-0"
          style={{ height: mainPaneHeight }}
        >
          <div
            ref={containerRef}
            className="h-full w-full"
            data-pane-id={paneId}
          />
          {overlay}
          {showSeries ? (
            <>
              <CandlestickSeries candles={candles} fitKey={fitKey} />
              <VolumeSeries candles={candles} theme={theme} />
              {activeIndicators
                .filter((item) => item.pane === 'overlay')
                .map((item) => (
                  <OverlayIndicatorSeries
                    key={item.instanceId}
                    seriesId={item.seriesId}
                    label={indicatorDisplayLabel(item.key, item.params)}
                    points={indicators[item.seriesId] ?? []}
                    color={resolveIndicatorColor(
                      item,
                      colorIndexForInstance(activeIndicators, item.instanceId),
                      theme,
                    )}
                    lineWidth={item.lineWidth ?? 2}
                    visible={item.visible !== false}
                  />
                ))}
              <ChartLegend
                candles={candles}
                theme={theme}
                overlayIndicators={overlayIndicators}
                indicators={indicators}
              />
              <DrawingsLayer symbolId={symbol?.id} timeframe={timeframe} />
            </>
          ) : null}
        </div>
        {chartReady
          ? subchartGroups.map((group, index) => {
              const groupKey = groupKeys[index]
              const paneIdKey = group.map((item) => item.seriesId).join('-')
              return (
                <div key={paneIdKey} className="shrink-0">
                  <PaneResizeHandle
                    onDrag={(deltaY) => {
                      if (index === 0) {
                        onResizeAboveSub(groupKey, deltaY)
                      } else {
                        onResizeBetweenSubs(groupKeys[index - 1], groupKey, deltaY)
                      }
                    }}
                  />
                  <IndicatorSubPane
                    paneId={paneIdKey}
                    group={group}
                    indicators={indicators}
                    chartHeight={getSubChartHeight(groupKey)}
                  />
                </div>
              )
            })
          : null}
        {showSeries ? (
          <ChartZoomControls barCount={Math.max(candles.length, 1)} />
        ) : null}
      </div>
    </ChartContext.Provider>
  )
}
