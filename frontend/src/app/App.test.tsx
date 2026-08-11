import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { USER_ID_STORAGE_KEY } from '@/constants/watchlist'
import { AUTH_TOKEN_STORAGE_KEY } from '@/constants/auth'
import { useChartStore } from '@/stores/chartStore'
import { useReplayStore } from '@/stores/replayStore'
import { useWatchlistStore } from '@/stores/watchlistStore'
import { useAuthStore } from '@/stores/authStore'
import { resetUserBootstrapLatch } from '@/services/userBootstrap'
import {
  deleteWatchlistCache,
  writeWatchlistCache,
} from '@/services/watchlistCache'

vi.mock('@/components/Chart/ChartContainer', () => ({
  ChartContainer: () => <div data-testid="chart-container" />,
}))

vi.mock('@/components/Layout/MultiChartLayout', () => ({
  MultiChartLayout: () => <div data-testid="chart-container" />,
}))

vi.mock('@/hooks/useReplayWs', () => ({
  useReplayWs: () => {},
}))

vi.mock('@/hooks/useReplayTick', () => ({
  useReplayTick: () => {},
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
  type: 'spot' as const,
  active: true,
  sortOrder: 1,
}

const mockEth = {
  ...mockSymbol,
  id: 'ETH/USDT',
  ticker: 'ETH/USDT',
  baseAsset: 'ETH',
  sortOrder: 2,
}

const mockUser = {
  id: 'user-test-1',
  name: 'Dev User',
  email: 'dev@local',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

const mockAuthToken = {
  access_token: 'test-access-token',
  token_type: 'bearer',
  user_id: 'user-test-1',
  email: 'dev@local',
  name: 'Dev User',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

const mockWatchlist = {
  id: 'wl-default',
  user_id: 'user-test-1',
  name: 'Default',
  is_default: true,
  sort_order: 0,
  symbols: ['BTC/USDT'],
  created_at: '2024-01-01T00:00:00Z',
}

function mockFetchResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers({ 'content-type': 'application/json' }),
    json: async () => body,
  }
}

type MockFetchResult = ReturnType<typeof mockFetchResponse>

function installDefaultFetch(
  overrides?: (
    url: string,
    method: string,
    init?: RequestInit,
  ) => MockFetchResult | Promise<MockFetchResult> | null,
) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      const method = (init?.method ?? 'GET').toUpperCase()
      const custom = overrides?.(url, method, init)
      if (custom) {
        return custom
      }

      // Phase 11 JWT bootstrap: register → login (no stored token)
      if (url.includes('/auth/register') && method === 'POST') {
        return mockFetchResponse(mockAuthToken, 201)
      }
      if (url.includes('/auth/login') && method === 'POST') {
        return mockFetchResponse(mockAuthToken)
      }
      if (url.includes('/auth/me') && method === 'GET') {
        return mockFetchResponse(mockUser)
      }

      if (url.endsWith('/users') && method === 'POST') {
        return mockFetchResponse(mockUser, 201)
      }

      if (url.includes('/users/user-test-1/watchlists') && method === 'GET') {
        return mockFetchResponse([mockWatchlist])
      }

      if (url.includes('/users/user-test-1/watchlists') && method === 'POST') {
        return mockFetchResponse(mockWatchlist, 201)
      }

      if (url.includes('/users/user-test-1') && method === 'GET') {
        return mockFetchResponse(mockUser)
      }

      if (url.includes('/symbols/ETH%2FUSDT')) {
        return mockFetchResponse(mockEth)
      }

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
}

describe('App', () => {
  beforeEach(async () => {
    localStorage.clear()
    resetUserBootstrapLatch()
    useAuthStore.getState().clear()
    useChartStore.setState({ symbol: null, replayMode: false })
    useReplayStore.getState().reset()
    useWatchlistStore.getState().reset()
    await deleteWatchlistCache('user-test-1')
    installDefaultFetch()
  })

  it('renders the chart route inside the app shell', async () => {
    window.history.pushState({}, '', '/')
    render(<App />)

    expect(await screen.findByRole('navigation', { name: 'Main' })).toBeInTheDocument()
    expect(screen.getByLabelText('Search symbols')).toBeInTheDocument()
    expect(screen.queryByText('Indicators')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Replay' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /replay/i })).not.toBeInTheDocument()
    expect(await screen.findByDisplayValue('BTC/USDT')).toBeInTheDocument()
    expect(await screen.findByRole('region', { name: 'Watchlist' })).toBeInTheDocument()
  })

  it('renders chart container on the home route', async () => {
    window.history.pushState({}, '', '/')
    render(<App />)

    expect(await screen.findByTestId('chart-container')).toBeInTheDocument()
  })

  it('bootstraps a user and loads the default watchlist on first startup', async () => {
    window.history.pushState({}, '', '/')
    render(<App />)

    await waitFor(() => {
      expect(localStorage.getItem(USER_ID_STORAGE_KEY)).toBe('user-test-1')
    })
    expect(await screen.findByText('BTC/USDT')).toBeInTheDocument()
    expect(useWatchlistStore.getState().selectedWatchlistId).toBe('wl-default')
  })

  it('paints IndexedDB cache before a deferred watchlist GET resolves', async () => {
    localStorage.setItem(USER_ID_STORAGE_KEY, 'user-test-1')
    localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, 'test-access-token')
    await writeWatchlistCache({
      version: 1,
      userId: 'user-test-1',
      selectedWatchlistId: 'wl-cached',
      confirmedAt: '2020-01-01T00:00:00.000Z',
      watchlists: [
        {
          id: 'wl-cached',
          userId: 'user-test-1',
          name: 'Cached',
          isDefault: true,
          sortOrder: 0,
          symbols: [mockEth],
          createdAt: '2020-01-01T00:00:00.000Z',
        },
      ],
    })

    let releaseWatchlists: (() => void) | undefined
    const watchlistsGate = new Promise<void>((resolve) => {
      releaseWatchlists = resolve
    })

    installDefaultFetch((url, method) => {
      if (url.includes('/users/user-test-1/watchlists') && method === 'GET') {
        return watchlistsGate.then(() => mockFetchResponse([mockWatchlist]))
      }
      return null
    })

    window.history.pushState({}, '', '/')
    render(<App />)

    expect(
      await screen.findByRole('button', { name: /ETH\/USDT/ }),
    ).toBeInTheDocument()
    expect(useWatchlistStore.getState().stale).toBe(true)

    releaseWatchlists?.()

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: /BTC\/USDT/ }),
      ).toBeInTheDocument()
    })
    expect(useWatchlistStore.getState().stale).toBe(false)
    expect(useWatchlistStore.getState().selectedWatchlistId).toBe('wl-default')
  })

  it('creates an empty Default watchlist when the API returns no lists', async () => {
    const emptyDefault = {
      ...mockWatchlist,
      symbols: [] as string[],
    }
    const createBodies: unknown[] = []

    installDefaultFetch((url, method, init) => {
      if (url.includes('/users/user-test-1/watchlists') && method === 'GET') {
        return mockFetchResponse([])
      }
      if (url.includes('/users/user-test-1/watchlists') && method === 'POST') {
        createBodies.push(JSON.parse(String(init?.body ?? '{}')))
        return mockFetchResponse(emptyDefault, 201)
      }
      return null
    })

    window.history.pushState({}, '', '/')
    render(<App />)

    await waitFor(() => {
      expect(useWatchlistStore.getState().selectedWatchlistId).toBe('wl-default')
    })
    expect(createBodies).toEqual([{ name: 'Default', symbols: [] }])
    expect(await screen.findByText(/No symbols yet/)).toBeInTheDocument()
  })
})
