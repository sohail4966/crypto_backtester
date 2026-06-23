import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fetchChartData, fetchIndicatorCatalog } from '@/services/chartDataAdapter'

describe('chartDataAdapter', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('normalizes indicator catalog rows at the API boundary', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => [
          {
            key: 'MACD_LINE',
            inputs: ['close'],
            shared_params: ['fast', 'slow', 'signal'],
            default_params: { fast: 12, slow: 26, signal: 9 },
            pane: 'subchart',
          },
          {
            key: 'EMA',
            inputs: ['close'],
            sharedParams: ['period'],
            defaultParams: { period: 20 },
          },
        ],
      })),
    )

    await expect(fetchIndicatorCatalog()).resolves.toEqual([
      {
        key: 'MACD_LINE',
        inputs: ['close'],
        sharedParams: ['fast', 'slow', 'signal'],
        defaultParams: { fast: 12, slow: 26, signal: 9 },
        pane: 'subchart',
      },
      {
        key: 'EMA',
        inputs: ['close'],
        sharedParams: ['period'],
        defaultParams: { period: 20 },
        pane: 'overlay',
      },
    ])
  })

  it('serializes indicator specs into the unified chart-data request', async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL) => ({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        symbol: {},
        timeframe: '1h',
        start: 100,
        end: 200,
        candles: [],
        indicators: {},
        signals: [],
        trades: [],
      }),
    }))
    vi.stubGlobal('fetch', fetchMock)

    await fetchChartData({
      symbolId: 'BTC/USDT',
      timeframe: '1h',
      start: 100,
      end: 200,
      limit: 500,
      indicators: [{ key: 'EMA', params: { period: 20 }, pane: 'overlay' }],
    })

    const url = new URL(String(fetchMock.mock.calls[0]?.[0]), 'http://localhost')
    expect(url.pathname).toBe('/api/v1/chart-data')
    expect(url.searchParams.get('indicators')).toBe(
      JSON.stringify([{ key: 'EMA', params: { period: 20 }, pane: 'overlay' }]),
    )
  })
})
