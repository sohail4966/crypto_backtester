import {
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
} from 'lightweight-charts'
import { CandlestickSeries } from '@/components/Chart/CandlestickSeries'
import { ChartContext } from '@/components/Chart/ChartContext'
import { VolumeSeries } from '@/components/Chart/VolumeSeries'
import { useChunkManager } from '@/hooks/useChunkManager'
import { useTheme } from '@/hooks/useTheme'
import { useChartStore } from '@/stores/chartStore'
import type { Theme } from '@/types/theme'
import { resolveChartColor } from '@/utils/color'

const MIN_CHART_HEIGHT = 420

interface ChartContainerProps {
  paneId?: string
  className?: string
}

function chartOptions(theme: Theme) {
  return {
    autoSize: false,
    layout: {
      background: { type: ColorType.Solid, color: resolveChartColor('var(--color-bg)', theme) },
      textColor: resolveChartColor('var(--color-text-secondary)', theme),
      attributionLogo: false,
    },
    grid: {
      vertLines: { color: resolveChartColor('var(--color-border)', theme) },
      horzLines: { color: resolveChartColor('var(--color-border)', theme) },
    },
    rightPriceScale: {
      borderColor: resolveChartColor('var(--color-border)', theme),
    },
    timeScale: {
      borderColor: resolveChartColor('var(--color-border)', theme),
      timeVisible: true,
      secondsVisible: false,
    },
    crosshair: {
      vertLine: { color: resolveChartColor('var(--color-accent)', theme) },
      horzLine: { color: resolveChartColor('var(--color-accent)', theme) },
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

  const { theme } = useTheme()
  const symbol = useChartStore((state) => state.symbol)
  const timeframe = useChartStore((state) => state.timeframe)
  const symbolId = symbol?.id

  const { candles, status, error, onVisibleRangeChange } = useChunkManager(
    symbolId,
    timeframe,
  )

  const [chartReady, setChartReady] = useState(false)

  useEffect(() => {
    themeRef.current = theme
  }, [theme])

  useEffect(() => {
    onRangeChangeRef.current = onVisibleRangeChange
  }, [onVisibleRangeChange])

  useEffect(() => {
    const container = containerRef.current
    if (!container) {
      return
    }

    const { width, height } = measureContainer(container)
    const chart = createChart(container, {
      ...chartOptions(themeRef.current),
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
    chart.applyOptions(chartOptions(theme))
    candleSeriesRef.current?.applyOptions(seriesColors(theme))
  }, [theme, chartReady])

  const contextValue = useMemo(
    () => ({
      chart: chartReady ? chartRef.current : null,
      candleSeries: chartReady ? candleSeriesRef.current : null,
      volumeSeries: chartReady ? volumeSeriesRef.current : null,
    }),
    [chartReady],
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
    <div className={className ?? 'relative min-h-[420px] w-full'}>
      <div
        ref={containerRef}
        className="h-full w-full"
        style={{ minHeight: MIN_CHART_HEIGHT }}
        data-pane-id={paneId}
      />
      {overlay}
      {chartReady && candles.length > 0 ? (
        <ChartContext.Provider value={contextValue}>
          <CandlestickSeries candles={candles} />
          <VolumeSeries candles={candles} theme={theme} />
        </ChartContext.Provider>
      ) : null}
    </div>
  )
}
