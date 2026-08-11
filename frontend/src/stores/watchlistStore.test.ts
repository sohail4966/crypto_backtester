import { beforeEach, describe, expect, it } from 'vitest'
import { useWatchlistStore } from '@/stores/watchlistStore'
import type { Watchlist } from '@/types/watchlist'
import type { Symbol } from '@/types/symbol'

const btc: Symbol = {
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

const eth: Symbol = {
  ...btc,
  id: 'ETH/USDT',
  ticker: 'ETH/USDT',
  baseAsset: 'ETH',
  sortOrder: 2,
}

function list(overrides: Partial<Watchlist> = {}): Watchlist {
  return {
    id: 'wl-1',
    userId: 'user-1',
    name: 'Default',
    isDefault: true,
    sortOrder: 0,
    symbols: [btc],
    createdAt: '2024-01-01T00:00:00Z',
    ...overrides,
  }
}

describe('watchlistStore', () => {
  beforeEach(() => {
    useWatchlistStore.getState().reset()
  })

  it('hydrates cache and marks it stale/refreshing', () => {
    useWatchlistStore.getState().hydrateFromCache({
      userId: 'user-1',
      watchlists: [list()],
      selectedWatchlistId: 'wl-1',
    })
    expect(useWatchlistStore.getState().status).toBe('hydrating')
    expect(useWatchlistStore.getState().stale).toBe(true)

    useWatchlistStore.getState().beginRefresh()
    expect(useWatchlistStore.getState().status).toBe('refreshing')
    expect(useWatchlistStore.getState().stale).toBe(true)
  })

  it('canonical replacement replaces cached data wholesale and preserves valid selection', () => {
    useWatchlistStore.getState().hydrateFromCache({
      userId: 'user-1',
      watchlists: [list()],
      selectedWatchlistId: 'wl-1',
    })

    const next = [
      list({ id: 'wl-2', name: 'Alt', isDefault: false, sortOrder: 1, symbols: [eth] }),
      list({ id: 'wl-1', symbols: [btc, eth] }),
    ]
    useWatchlistStore.getState().applyCanonical(next, 'wl-1')
    expect(useWatchlistStore.getState().selectedWatchlistId).toBe('wl-1')
    expect(useWatchlistStore.getState().watchlists[0]?.id).toBe('wl-2')
    expect(useWatchlistStore.getState().stale).toBe(false)
    expect(useWatchlistStore.getState().status).toBe('ready')
  })

  it('falls back selection when preferred ID disappears', () => {
    useWatchlistStore.getState().applyCanonical(
      [
        list({ id: 'a', isDefault: false, sortOrder: 2 }),
        list({ id: 'b', isDefault: true, sortOrder: 9 }),
      ],
      'missing',
    )
    expect(useWatchlistStore.getState().selectedWatchlistId).toBe('b')
  })

  it('duplicate detection uses symbol ID and optimistic append preserves order', () => {
    useWatchlistStore.getState().applyCanonical([list({ symbols: [btc] })], 'wl-1')
    expect(useWatchlistStore.getState().beginOptimisticAdd('wl-1', btc)).toBe(false)
    expect(useWatchlistStore.getState().watchlists[0]?.symbols).toHaveLength(1)

    expect(useWatchlistStore.getState().beginOptimisticAdd('wl-1', eth)).toBe(true)
    expect(useWatchlistStore.getState().watchlists[0]?.symbols.map((s) => s.id)).toEqual([
      'BTC/USDT',
      'ETH/USDT',
    ])
    expect(useWatchlistStore.getState().pendingWatchlistIds).toContain('wl-1')
  })

  it('applies a settled response to its captured target without changing selection', () => {
    useWatchlistStore.getState().applyCanonical(
      [
        list({ id: 'wl-1', symbols: [btc] }),
        list({ id: 'wl-2', name: 'Other', isDefault: false, symbols: [] }),
      ],
      'wl-1',
    )
    useWatchlistStore.getState().beginOptimisticAdd('wl-1', eth)
    useWatchlistStore.getState().setSelectedWatchlistId('wl-2')
    useWatchlistStore.getState().commitWatchlist(
      list({ id: 'wl-1', symbols: [btc, eth] }),
    )

    expect(useWatchlistStore.getState().selectedWatchlistId).toBe('wl-2')
    expect(
      useWatchlistStore.getState().watchlists.find((item) => item.id === 'wl-1')
        ?.symbols,
    ).toHaveLength(2)
  })

  it('rollback restores the exact confirmed snapshot', () => {
    useWatchlistStore.getState().applyCanonical([list({ symbols: [btc] })], 'wl-1')
    useWatchlistStore.getState().beginOptimisticAdd('wl-1', eth)
    useWatchlistStore.getState().rollbackWatchlist('wl-1')
    expect(useWatchlistStore.getState().watchlists[0]?.symbols).toEqual([btc])
    expect(useWatchlistStore.getState().pendingWatchlistIds).toEqual([])
  })

  it('tracks pending per watchlist independently', () => {
    useWatchlistStore.getState().applyCanonical(
      [
        list({ id: 'wl-1', symbols: [] }),
        list({ id: 'wl-2', name: 'Other', isDefault: false, symbols: [] }),
      ],
      'wl-1',
    )
    useWatchlistStore.getState().beginOptimisticAdd('wl-1', btc)
    useWatchlistStore.getState().beginOptimisticAdd('wl-2', eth)
    expect(useWatchlistStore.getState().pendingWatchlistIds).toEqual(['wl-1', 'wl-2'])
    useWatchlistStore.getState().rollbackWatchlist('wl-1')
    expect(useWatchlistStore.getState().pendingWatchlistIds).toEqual(['wl-2'])
  })
})
