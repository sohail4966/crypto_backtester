import { beforeEach, describe, expect, it } from 'vitest'
import { watchlistCacheKey } from '@/constants/watchlist'
import {
  deleteWatchlistCache,
  isValidWatchlistCache,
  readWatchlistCache,
  writeWatchlistCache,
} from '@/services/watchlistCache'
import type { WatchlistCacheV1 } from '@/types/watchlist'
import type { Symbol } from '@/types/symbol'
import { del as idbDel, get as idbGet } from 'idb-keyval'

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

function validCache(overrides: Partial<WatchlistCacheV1> = {}): WatchlistCacheV1 {
  return {
    version: 1,
    userId: 'user-1',
    selectedWatchlistId: 'wl-1',
    confirmedAt: '2020-01-01T00:00:00.000Z',
    watchlists: [
      {
        id: 'wl-1',
        userId: 'user-1',
        name: 'Default',
        isDefault: true,
        sortOrder: 0,
        symbols: [btc],
        createdAt: '2020-01-01T00:00:00.000Z',
      },
    ],
    ...overrides,
  }
}

describe('watchlistCache', () => {
  beforeEach(async () => {
    await idbDel(watchlistCacheKey('user-1'))
    await idbDel(watchlistCacheKey('user-2'))
  })

  it('round-trips a v1 confirmed snapshot', async () => {
    const cache = validCache()
    await writeWatchlistCache(cache)
    await expect(readWatchlistCache('user-1')).resolves.toEqual(cache)
  })

  it('scopes keys by user', async () => {
    await writeWatchlistCache(validCache({ userId: 'user-1' }))
    await writeWatchlistCache(
      validCache({
        userId: 'user-2',
        selectedWatchlistId: null,
        watchlists: [],
      }),
    )
    await expect(readWatchlistCache('user-1')).resolves.toMatchObject({ userId: 'user-1' })
    await expect(readWatchlistCache('user-2')).resolves.toMatchObject({
      userId: 'user-2',
      watchlists: [],
    })
  })

  it('rejects the whole record for malformed nested symbols', async () => {
    const bad = validCache()
    // @ts-expect-error intentional malformed cache
    bad.watchlists[0].symbols[0] = { id: 'BTC/USDT' }
    expect(isValidWatchlistCache(bad, 'user-1')).toBe(false)

    const { set } = await import('idb-keyval')
    await set(watchlistCacheKey('user-1'), bad)
    await expect(readWatchlistCache('user-1')).resolves.toBeNull()
    await expect(idbGet(watchlistCacheKey('user-1'))).resolves.toBeUndefined()
  })

  it('rejects wrong-user data and unsupported versions', () => {
    expect(isValidWatchlistCache(validCache({ userId: 'other' }), 'user-1')).toBe(false)
    expect(
      isValidWatchlistCache({ ...validCache(), version: 2 } as unknown, 'user-1'),
    ).toBe(false)
  })

  it('retains old but valid confirmed snapshots without age expiry', async () => {
    const old = validCache({ confirmedAt: '2018-01-01T00:00:00.000Z' })
    await writeWatchlistCache(old)
    await expect(readWatchlistCache('user-1')).resolves.toEqual(old)
  })

  it('deletes stale-user cache', async () => {
    await writeWatchlistCache(validCache())
    await deleteWatchlistCache('user-1')
    await expect(readWatchlistCache('user-1')).resolves.toBeNull()
  })
})
