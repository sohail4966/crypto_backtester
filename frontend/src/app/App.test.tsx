import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useChartStore } from '@/stores/chartStore'
import { useReplayStore } from '@/stores/replayStore'

vi.mock('@/components/Chart/ChartContainer', () => ({
  ChartContainer: () => <div data-testid="chart-container" />,
}))

import { App } from './App'

const mockSymbol = {
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

function mockFetchResponse(body: unknown) {
  return {
    ok: true,
    status: 200,
    headers: new Headers({ 'content-type': 'application/json' }),
    json: async () => body,
  }
}

describe('App', () => {
  beforeEach(() => {
    useChartStore.setState({ symbol: null, replayMode: false })
    useReplayStore.getState().resetSession()
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input)

        if (url.includes('/symbols/BTC%2FUSDT') && url.includes('data-range')) {
          return mockFetchResponse({
            symbolId: 'BTC/USDT',
            timeframe: '1h',
            earliest: 1_700_000_000,
            latest: 1_700_500_000,
            barCount: 500,
          })
        }

        if (url.includes('/symbols/BTC%2FUSDT')) {
          return mockFetchResponse(mockSymbol)
        }

        if (url.includes('/chart-data')) {
          return mockFetchResponse({
            symbol: mockSymbol,
            timeframe: '1h',
            start: 1_700_000_000,
            end: 1_700_500_000,
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
            signals: [],
            trades: [],
          })
        }

        if (url.includes('/symbols/search')) {
          return mockFetchResponse([mockSymbol])
        }

        return mockFetchResponse({})
      }),
    )
  })

  it('renders the chart route inside the app shell', async () => {
    window.history.pushState({}, '', '/')
    render(<App />)

    expect(screen.getByRole('navigation', { name: 'Main' })).toBeInTheDocument()
    expect(screen.getByLabelText('Search symbols')).toBeInTheDocument()
    expect(screen.queryByText('Indicators')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Replay' })).toBeInTheDocument()
    expect(await screen.findByDisplayValue('BTC/USDT')).toBeInTheDocument()
  })

  it('redirects legacy /replay route to chart', async () => {
    window.history.pushState({}, '', '/replay')
    render(<App />)

    expect(await screen.findByTestId('chart-container')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Replay' })).not.toBeInTheDocument()
  })

  it('toggles replay mode from the topbar', async () => {
    window.history.pushState({}, '', '/')
    render(<App />)

    await screen.findByDisplayValue('BTC/USDT')
    fireEvent.click(screen.getByRole('button', { name: 'Replay' }))
    expect(useChartStore.getState().replayMode).toBe(true)
    expect(useReplayStore.getState().phase).toBe('pick_anchor')
  })
})
