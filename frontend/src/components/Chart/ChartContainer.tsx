import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import {
  ColorType,
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
import { OverlayIndicatorSeries } from '@/components/Indicators/OverlayIndicatorSeries'
import { IndicatorSubPane } from '@/components/Indicators/IndicatorSubPane'
import { ChartZoomControls } from '@/components/Chart/ChartZoomControls'
import { VolumeSeries } from '@/components/Chart/VolumeSeries'
import { FIT_RIGHT_OFFSET_BARS } from '@/constants/chart'
import type { ChartTimezoneId } from '@/constants/timezone'
import { useChunkManager } from '@/hooks/useChunkManager'
import { useTheme } from '@/hooks/useTheme'
import { useChartStore } from '@/stores/chartStore'
import { useIndicatorStore } from '@/stores/indicatorStore'
import type { OHLCVBar } from '@/types/candle'
import type { ActiveIndicator, IndicatorSpec } from '@/types/indicator'
import { isMacdKey } from '@/types/indicator'
import type { Theme } from '@/types/theme'
import { resolveChartColor } from '@/utils/color'
import {
  createChartTimezoneFormatters,
  loadChartTimezonePreference,
  resolveChartTimeZone,
} from '@/utils/chartTimezone'
import { specsCacheKey } from '@/utils/indicatorId'
import { indicatorDisplayLabel } from '@/utils/indicatorDisplay'
import { candleCloseAtTime } from '@/utils/crosshairSync'

const MIN_CHART_HEIGHT = 420

interface ChartContainerProps {
  paneId?: string
  className?: string
}

function chartOptions(theme: Theme, showGrid: boolean, timezone: ChartTimezoneId) {
  const { timeFormatter, tickMarkFormatter } = createChartTimezoneFormatters(
    resolveChartTimeZone(timezone),
  )
  const gridColor = resolveChartColor('var(--color-border)', theme)
  return {
    autoSize: false,
    layout: {
      background: { type: ColorType.Solid, color: resolveChartColor('var(--color-bg)', theme) },
      textColor: resolveChartColor('var(--color-text-secondary)', theme),
      attributionLogo: false,
    },
    grid: {
      vertLines: { visible: showGrid, color: gridColor },
      horzLines: { visible: showGrid, color: gridColor },
    },
    rightPriceScale: {
      borderColor: resolveChartColor('var(--color-border)', theme),
    },
    localization: {
      timeFormatter,
    },
    timeScale: {
      borderColor: resolveChartColor('var(--color-border)', theme),
      timeVisible: true,
      secondsVisible: false,
      rightOffset: FIT_RIGHT_OFFSET_BARS,
      tickMarkFormatter,
    },
    crosshair: {
      vertLine: { color: resolveChartColor('var(--color-accent)', theme) },
      horzLine: { color: resolveChartColor('var(--color-accent)', theme) },
    },
    handleScroll: {
      mouseWheel: true,
      pressedMouseMove: true,
      horzTouchDrag: true,
      vertTouchDrag: false,
    },
    handleScale: {
      mouseWheel: true,
      pinch: true,
      axisPressedMouseMove: { time: true, price: true },
      axisDoubleClickReset: { time: true, price: true },
    },
  } as const
}

function seriesColors(theme: Theme) {
  return {
    upColor: resolveChartColor('var(--color-bull)', theme),
    downColor: resolveChartColor('var(--color-bear)', theme),
    borderUpColor: resolveChartColor('var(--color-bull)', theme),
    borderDownColor: resolveChartColor('var(--color-bear)', theme),
    wickUpColor: resolveChartColor('var(--color-bull)', theme),
    wickDownColor: resolveChartColor('var(--color-bear)', theme),
  }
}

function measureContainer(container: HTMLDivElement) {
  const { width, height } = container.getBoundingClientRect()
  return {
    width: Math.max(1, Math.floor(width)),
    height: Math.max(MIN_CHART_HEIGHT, Math.floor(height)),
  }
}

export function ChartContainer({ paneId = 'main', className }: ChartContainerProps) {
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
  const candlesRef = useRef<OHLCVBar[]>([])

  const { theme } = useTheme()
  const symbol = useChartStore((state) => state.symbol)
  const timeframe = useChartStore((state) => state.timeframe)
  const timezone = useChartStore((state) => state.timezone)
  const showGrid = useChartStore((state) => state.showGrid)
  const pulseZoomControls = useChartStore((state) => state.pulseZoomControls)
  const activeIndicators = useIndicatorStore((state) => state.active)

  const indicatorSpecs = useMemo((): IndicatorSpec[] => {
    const seen = new Set<string>()
    const specs: IndicatorSpec[] = []
    for (const item of activeIndicators) {
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
      const groupKey = isMacdKey(item.key)
        ? `MACD:${JSON.stringify(item.params)}`
        : item.seriesId
      const list = groups.get(groupKey) ?? []
      list.push(item)
      groups.set(groupKey, list)
    }
    return [...groups.values()]
  }, [activeIndicators])

  const symbolId = symbol?.id
  const indicatorSpecsKey = specsCacheKey(indicatorSpecs)
  const fitKey = `${symbolId ?? 'none'}-${timeframe}-${indicatorSpecsKey}`

  const { candles, indicators, status, error, onVisibleRangeChange } = useChunkManager(
    symbolId,
    timeframe,
    indicatorSpecs,
  )

  const [chartReady, setChartReady] = useState(false)
  const [crosshairTime, setCrosshairTime] = useState<number | null>(null)

  candlesRef.current = candles

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
        const close = candleCloseAtTime(candlesRef.current, time)
        if (close != null) {
          main.setCrosshairPosition(close, time, candleSeries)
        }
      }

      subChartsRef.current.forEach((handle) => {
        const series = handle.getPrimarySeries()
        const price = handle.getPriceAtTime(time)
        if (series && price != null) {
          handle.chart.setCrosshairPosition(price, time, series)
        }
      })
    } finally {
      syncingCrosshairRef.current = false
    }
  }, [])

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
    onRangeChangeRef.current = onVisibleRangeChange
  }, [onVisibleRangeChange])

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

  // Reveal bottom zoom bar briefly after mouse-wheel zoom on the chart.
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

    const { width, height } = measureContainer(container)
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

    chart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      onRangeChangeRef.current(range)
    })

    chartRef.current = chart
    candleSeriesRef.current = candleSeries
    volumeSeriesRef.current = volumeSeries
    setChartReady(true)

    const observer = new ResizeObserver(() => {
      if (!chartRef.current || !containerRef.current) {
        return
      }
      const next = measureContainer(containerRef.current)
      chartRef.current.applyOptions(next)
    })
    observer.observe(container)

    return () => {
      observer.disconnect()
      chart.remove()
      chartRef.current = null
      candleSeriesRef.current = null
      volumeSeriesRef.current = null
      setChartReady(false)
    }
  }, [paneId])

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
  } else if (status === 'loading' || status === 'idle') {
    overlay = (
      <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center bg-bg/80 text-sm text-text-secondary">
        Loading chart…
      </div>
    )
  } else if (status === 'error') {
    overlay = (
      <div className="absolute inset-0 z-10 flex items-center justify-center bg-bg/90 px-6 text-center text-sm text-bear">
        {error?.message ?? 'Failed to load chart data.'}
      </div>
    )
  } else if (candles.length === 0) {
    overlay = (
      <div className="absolute inset-0 z-10 flex items-center justify-center bg-bg/90 px-6 text-center text-sm text-text-secondary">
        No candle data returned for this symbol and timeframe.
      </div>
    )
  }

  return (
    <ChartContext.Provider value={contextValue}>
      <div
        className={className ?? 'relative flex min-h-[420px] w-full flex-col'}
        onMouseLeave={clearCrosshair}
      >
        <div className="relative min-h-0 flex-1">
          <div
            ref={containerRef}
            className="h-full w-full"
            style={{ minHeight: MIN_CHART_HEIGHT }}
            data-pane-id={paneId}
          />
          {overlay}
          {chartReady && candles.length > 0 ? (
            <>
              <CandlestickSeries candles={candles} fitKey={fitKey} />
              <VolumeSeries candles={candles} theme={theme} />
              {overlayIndicators.map((item, index) => (
                <OverlayIndicatorSeries
                  key={item.instanceId}
                  seriesId={item.seriesId}
                  label={indicatorDisplayLabel(item.key, item.params)}
                  points={indicators[item.seriesId] ?? []}
                  colorIndex={index}
                />
              ))}
              <ChartLegend
                candles={candles}
                theme={theme}
                overlayIndicators={overlayIndicators}
                indicators={indicators}
              />
              <ChartZoomControls barCount={candles.length} />
            </>
          ) : null}
        </div>
        {chartReady && subchartGroups.length > 0
          ? subchartGroups.map((group) => (
              <IndicatorSubPane
                key={group.map((item) => item.seriesId).join('-')}
                paneId={group.map((item) => item.seriesId).join('-')}
                group={group}
                indicators={indicators}
              />
            ))
          : null}
      </div>
    </ChartContext.Provider>
  )
}
