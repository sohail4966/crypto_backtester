import { render, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ChartContainer } from '@/components/Chart/ChartContainer'
import { useChartStore } from '@/stores/chartStore'
import { useIndicatorStore } from '@/stores/indicatorStore'
import { useReplayStore } from '@/stores/replayStore'
import type { Symbol } from '@/types/symbol'

let renderedSeries: 'live' | 'replay' = 'live'

vi.mock('lightweight-charts', () => ({
  ColorType: { Solid: 'Solid' },
  createChart: vi.fn(() => ({
    addCandlestickSeries: vi.fn(() => ({
      applyOptions: vi.fn(),
      setData: vi.fn(),
    })),
    addHistogramSeries: vi.fn(() => ({
      applyOptions: vi.fn(),
      setData: vi.fn(),
    })),
    applyOptions: vi.fn(),
    clearCrosshairPosition: vi.fn(),
    priceScale: vi.fn(() => ({ applyOptions: vi.fn() })),
    remove: vi.fn(),
    subscribeCrosshairMove: vi.fn(),
    unsubscribeCrosshairMove: vi.fn(),
    subscribeClick: vi.fn(),
    unsubscribeClick: vi.fn(),
    timeScale: vi.fn(() => ({
      getVisibleLogicalRange: vi.fn(() => null),
      setVisibleLogicalRange: vi.fn(),
      subscribeVisibleLogicalRangeChange: vi.fn(),
      unsubscribeVisibleLogicalRangeChange: vi.fn(),
    })),
  })),
}))

vi.mock('@/hooks/useTheme', () => ({
  useTheme: () => ({ theme: 'dark', toggleTheme: vi.fn() }),
}))

vi.mock('@/hooks/useChunkManager', () => ({
  useChunkManager: () => ({
    candles: [
      { time: 1_700_000_000, open: 100, high: 110, low: 90, close: 105, volume: 12 },
      { time: 1_700_000_100, open: 105, high: 115, low: 100, close: 110, volume: 10 },
    ],
    indicators: {},
    status: 'ready',
    error: null,
    onVisibleRangeChange: vi.fn(),
  }),
}))

vi.mock('@/components/Chart/CandlestickSeries', () => ({
  CandlestickSeries: () => {
    renderedSeries = 'live'
    return null
  },
}))

vi.mock('@/components/Chart/VolumeSeries', () => ({ VolumeSeries: () => null }))
vi.mock('@/components/Chart/ChartLegend', () => ({ ChartLegend: () => null }))
vi.mock('@/components/Chart/ChartZoomControls', () => ({ ChartZoomControls: () => null }))
vi.mock('@/components/Indicators/OverlayIndicatorSeries', () => ({ OverlayIndicatorSeries: () => null }))
vi.mock('@/components/Indicators/IndicatorSubPane', () => ({ IndicatorSubPane: () => null }))

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

describe('ChartContainer replay data path', () => {
  beforeEach(() => {
    renderedSeries = 'live'
    useChartStore.setState({
      symbol: mockSymbol,
      timeframe: '1h',
      timezone: 'local',
      showGrid: true,
      showVolume: true,
      zoomControlsPulse: 0,
    })
    useIndicatorStore.setState({ active: [], settingsInstanceId: null })
    useReplayStore.getState().resetSession()
    useReplayStore.setState({
      phase: 'ready',
      sessionId: 'session-1',
      startAnchor: 1_700_000_100,
      baselineCandles: [
        { time: 1_700_000_000, open: 100, high: 110, low: 90, close: 105, volume: 12 },
      ],
      candles: [],
    })
  })

  it('keeps the live candlestick series mounted during replay', async () => {
    render(<ChartContainer replaySessionActive />)

    await waitFor(() => expect(renderedSeries).toBe('live'))
  })
})
