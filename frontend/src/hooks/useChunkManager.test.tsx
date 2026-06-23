import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import type { Logical, LogicalRange } from 'lightweight-charts'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useChunkManager } from '@/hooks/useChunkManager'
import { fetchChartData, resolveCandleDataRange } from '@/services/chartDataAdapter'
import type { ChartDataRequest, ChartDataResponse } from '@/types/chartData'
import type { OHLCVBar } from '@/types/candle'

vi.mock('@/services/chartDataAdapter', () => ({
  fetchChartData: vi.fn(),
  resolveCandleDataRange: vi.fn(),
}))

const mockedFetchChartData = vi.mocked(fetchChartData)
const mockedResolveCandleDataRange = vi.mocked(resolveCandleDataRange)

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((promiseResolve, promiseReject) => {
    resolve = promiseResolve
    reject = promiseReject
  })
  return { promise, resolve, reject }
}

function bar(time: number, close: number): OHLCVBar {
  return {
    time,
    open: close,
    high: close + 1,
    low: close - 1,
    close,
    volume: close * 100,
  }
}

function logicalRange(from: number, to: number): LogicalRange {
  return { from: from as Logical, to: to as Logical }
}

function chartResponse(request: ChartDataRequest, candles: OHLCVBar[]): ChartDataResponse {
  return {
    symbol: {
      id: request.symbolId,
      ticker: request.symbolId,
      exchange: 'binance',
      baseAsset: request.symbolId.split('/')[0] ?? request.symbolId,
      quoteAsset: request.symbolId.split('/')[1] ?? 'USDT',
      tickSize: 0.01,
      lotSize: 0.00001,
      type: 'spot',
      active: true,
      sortOrder: 1,
    },
    timeframe: request.timeframe,
    start: request.start,
    end: request.end,
    candles,
    indicators: {},
    signals: [],
    trades: [],
  }
}

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

describe('useChunkManager', () => {
  beforeEach(() => {
    mockedFetchChartData.mockReset()
    mockedResolveCandleDataRange.mockReset()
    mockedResolveCandleDataRange.mockResolvedValue({
      symbolId: 'BTC/USDT',
      timeframe: '1m',
      earliest: 0,
      latest: 30_000,
      barCount: 501,
    })
  })

  it('ignores a stale prefetch response after symbol changes', async () => {
    const stalePrefetch = deferred<ChartDataResponse>()

    mockedFetchChartData.mockImplementation((request) => {
      if (request.symbolId === 'BTC/USDT' && request.start === 0) {
        return stalePrefetch.promise
      }
      const baseClose = request.symbolId === 'BTC/USDT' ? 100 : 200
      return Promise.resolve(
        chartResponse(request, [
          bar(request.start, baseClose),
          bar(request.end, baseClose + 1),
        ]),
      )
    })

    const { result, rerender } = renderHook(
      ({ symbolId }) => useChunkManager(symbolId, '1m', []),
      {
        initialProps: { symbolId: 'BTC/USDT' },
        wrapper,
      },
    )

    await waitFor(() => expect(result.current.status).toBe('ready'))

    act(() => {
      result.current.onVisibleRangeChange(logicalRange(150, 250))
      result.current.onVisibleRangeChange(logicalRange(50, 150))
    })
    expect(mockedFetchChartData).toHaveBeenCalledWith(
      expect.objectContaining({ symbolId: 'BTC/USDT', start: 0, end: 0 }),
    )

    rerender({ symbolId: 'ETH/USDT' })
    await waitFor(() => expect(result.current.status).toBe('ready'))
    await waitFor(() => expect(result.current.candles[0]?.close).toBe(200))

    await act(async () => {
      stalePrefetch.resolve(chartResponse(
        {
          symbolId: 'BTC/USDT',
          timeframe: '1m',
          start: 0,
          end: 0,
          limit: 500,
          indicators: [],
        },
        [bar(0, 999)],
      ))
      await stalePrefetch.promise
    })

    expect(result.current.candles.map((item) => item.close)).toEqual([200, 201])
  })
})
