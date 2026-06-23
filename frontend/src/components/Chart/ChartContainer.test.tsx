import { act, render, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ChartContainer } from '@/components/Chart/ChartContainer'
import { useChartStore } from '@/stores/chartStore'
import { useIndicatorStore } from '@/stores/indicatorStore'
import type { Symbol } from '@/types/symbol'

const capturedFitKeys: string[] = []
const chartMocks = vi.hoisted(() => {
  const timeScale = {
    getVisibleLogicalRange: vi.fn(() => null),
    setVisibleLogicalRange: vi.fn(),
    subscribeVisibleLogicalRangeChange: vi.fn(),
    unsubscribeVisibleLogicalRangeChange: vi.fn(),
  }
  const chart = {
    addCandlestickSeries: vi.fn(() => ({
      applyOptions: vi.fn(),
    })),
    addHistogramSeries: vi.fn(() => ({
      applyOptions: vi.fn(),
      setData: vi.fn(),
    })),
    applyOptions: vi.fn(),
    clearCrosshairPosition: vi.fn(),
    priceScale: vi.fn(() => ({
      applyOptions: vi.fn(),
    })),
    remove: vi.fn(),
    subscribeCrosshairMove: vi.fn(),
    timeScale: vi.fn(() => timeScale),
    unsubscribeCrosshairMove: vi.fn(),
  }
  return { chart, timeScale }
})

vi.mock('lightweight-charts', () => ({
  ColorType: { Solid: 'Solid' },
  createChart: vi.fn(() => chartMocks.chart),
}))

vi.mock('@/hooks/useTheme', () => ({
  useTheme: () => ({ theme: 'dark', toggleTheme: vi.fn() }),
}))

vi.mock('@/hooks/useChunkManager', () => ({
  useChunkManager: () => ({
    candles: [
      {
        time: 1_700_000_000,
        open: 100,
        high: 110,
        low: 90,
        close: 105,
        volume: 12,
      },
    ],
    indicators: {},
    status: 'ready',
    error: null,
    onVisibleRangeChange: vi.fn(),
  }),
}))

vi.mock('@/components/Chart/CandlestickSeries', () => ({
  CandlestickSeries: ({ fitKey }: { fitKey: string }) => {
    capturedFitKeys.push(fitKey)
    return null
  },
}))

vi.mock('@/components/Chart/VolumeSeries', () => ({
  VolumeSeries: () => null,
}))

vi.mock('@/components/Chart/ChartLegend', () => ({
  ChartLegend: () => null,
}))

vi.mock('@/components/Chart/ChartZoomControls', () => ({
  ChartZoomControls: () => null,
}))

vi.mock('@/components/Indicators/OverlayIndicatorSeries', () => ({
  OverlayIndicatorSeries: () => null,
}))

vi.mock('@/components/Indicators/IndicatorSubPane', () => ({
  IndicatorSubPane: () => null,
}))

const mockSymbol: Symbol = {
  id: 'BTC/USDT',
  ticker: 'BTC/USDT',
  exchange: 'binance',
  baseAsset: 'BTC',
  quoteAsset: 'USDT',
  tickSize: 0.01,
  lotSize: 0.00001,
  type: 'spot',
  active: true,
  sortOrder: 1,
}

describe('ChartContainer', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    capturedFitKeys.length = 0
    useChartStore.setState({
      symbol: mockSymbol,
      timeframe: '1h',
      timezone: 'local',
      showGrid: true,
      showVolume: true,
      zoomControlsPulse: 0,
    })
    useIndicatorStore.setState({
      active: [],
      settingsInstanceId: null,
    })
  })

  it('keeps the candle fit key stable when indicator specs change', async () => {
    render(<ChartContainer />)

    await waitFor(() => expect(capturedFitKeys.length).toBeGreaterThan(0))
    const initialFitKey = capturedFitKeys.at(-1)

    act(() => {
      useIndicatorStore.setState({
        active: [
          {
            instanceId: 'ema-20',
            key: 'EMA',
            params: { period: 20 },
            pane: 'overlay',
            seriesId: 'EMA_20',
            visible: true,
          },
        ],
      })
    })

    await waitFor(() => expect(capturedFitKeys.length).toBeGreaterThan(1))

    expect(capturedFitKeys.at(-1)).toBe(initialFitKey)
  })

  it('unsubscribes the main visible-range listener before removing the chart', async () => {
    const { unmount } = render(<ChartContainer />)

    await waitFor(() =>
      expect(chartMocks.timeScale.subscribeVisibleLogicalRangeChange).toHaveBeenCalledTimes(1),
    )
    const subscribedCallback =
      chartMocks.timeScale.subscribeVisibleLogicalRangeChange.mock.calls[0]?.[0]

    unmount()

    expect(chartMocks.timeScale.unsubscribeVisibleLogicalRangeChange).toHaveBeenCalledWith(
      subscribedCallback,
    )
    expect(chartMocks.chart.remove).toHaveBeenCalled()
  })
})
