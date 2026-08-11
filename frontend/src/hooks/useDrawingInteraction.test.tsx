import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { IChartApi, ISeriesApi, MouseEventParams } from 'lightweight-charts'
import { useDrawingInteraction } from '@/hooks/useDrawingInteraction'
import { useChartStore } from '@/stores/chartStore'
import { useDrawingStore } from '@/stores/drawingStore'
import { useReplayStore } from '@/stores/replayStore'
import type { Symbol } from '@/types/symbol'

vi.mock('@/hooks/useTheme', () => ({
  useTheme: () => ({ theme: 'dark', toggleTheme: vi.fn() }),
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

describe('useDrawingInteraction', () => {
  let clickHandler: ((param: MouseEventParams) => void) | null = null

  const candleSeries = {
    coordinateToPrice: vi.fn((y: number) => y),
    priceToCoordinate: vi.fn((price: number) => price),
  } as unknown as ISeriesApi<'Candlestick'>

  const chart = {
    subscribeClick: vi.fn((handler: (param: MouseEventParams) => void) => {
      clickHandler = handler
    }),
    unsubscribeClick: vi.fn(),
    timeScale: () => ({
      timeToCoordinate: vi.fn(() => 10),
    }),
  } as unknown as IChartApi

  beforeEach(() => {
    clickHandler = null
    vi.clearAllMocks()
    useDrawingStore.setState({
      drawings: [],
      activeTool: null,
      selectedId: null,
      draft: null,
      hydrated: true,
    })
    useChartStore.setState({
      symbol: mockSymbol,
      timeframe: '1h',
    })
    useReplayStore.setState({ phase: 'inactive' })
  })

  it('creates a horizontal line on one click with hex color', () => {
    useDrawingStore.getState().setActiveTool('horizontal_line')
    renderHook(() =>
      useDrawingInteraction({ chart, candleSeries, chartReady: true }),
    )

    act(() => {
      clickHandler?.({
        time: 1_700_000_000,
        point: { x: 10, y: 250 },
      } as MouseEventParams)
    })

    const drawings = useDrawingStore.getState().drawings
    expect(drawings).toHaveLength(1)
    expect(drawings[0]?.type).toBe('horizontal_line')
    expect(drawings[0]?.color.startsWith('#')).toBe(true)
    expect(useDrawingStore.getState().activeTool).toBeNull()
  })

  it('sorts trend-line points by time when second click is earlier', () => {
    useDrawingStore.getState().setActiveTool('trend_line')
    renderHook(() =>
      useDrawingInteraction({ chart, candleSeries, chartReady: true }),
    )

    act(() => {
      clickHandler?.({
        time: 200,
        point: { x: 20, y: 100 },
      } as MouseEventParams)
    })
    act(() => {
      clickHandler?.({
        time: 100,
        point: { x: 10, y: 120 },
      } as MouseEventParams)
    })

    const drawing = useDrawingStore.getState().drawings[0]
    expect(drawing?.type).toBe('trend_line')
    if (drawing?.type === 'trend_line') {
      expect(drawing.p1.time).toBe(100)
      expect(drawing.p2.time).toBe(200)
    }
  })

  it('ignores clicks during replay pick_anchor', () => {
    useReplayStore.setState({ phase: 'pick_anchor' })
    useDrawingStore.getState().setActiveTool('horizontal_line')
    renderHook(() =>
      useDrawingInteraction({ chart, candleSeries, chartReady: true }),
    )

    act(() => {
      clickHandler?.({
        time: 1_700_000_000,
        point: { x: 10, y: 250 },
      } as MouseEventParams)
    })

    expect(useDrawingStore.getState().drawings).toHaveLength(0)
  })
})
