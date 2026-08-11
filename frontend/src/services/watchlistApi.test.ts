import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  createWatchlist,
  listWatchlists,
  replaceWatchlistSymbols,
} from '@/services/watchlistApi'

vi.mock('@/services/api', async () => {
  const actual = await vi.importActual<typeof import('@/services/api')>('@/services/api')
  return {
    ...actual,
    apiRequest: vi.fn(),
  }
})

import { apiRequest } from '@/services/api'

const mockedApi = vi.mocked(apiRequest)

describe('watchlistApi', () => {
  beforeEach(() => {
    mockedApi.mockReset()
    mockedApi.mockResolvedValue({})
  })

  it('lists watchlists with nested URL encoding', async () => {
    await listWatchlists('user/1')
    expect(mockedApi).toHaveBeenCalledWith('/users/user%2F1/watchlists')
  })

  it('creates with empty symbols array', async () => {
    await createWatchlist('user-1', 'Default', [])
    expect(mockedApi).toHaveBeenCalledWith('/users/user-1/watchlists', {
      method: 'POST',
      body: JSON.stringify({ name: 'Default', symbols: [] }),
    })
  })

  it('replaces with the complete ordered ID list', async () => {
    await replaceWatchlistSymbols('user-1', 'wl-1', ['BTC/USDT', 'ETH/USDT'])
    expect(mockedApi).toHaveBeenCalledWith(
      '/users/user-1/watchlists/wl-1/symbols',
      {
        method: 'PUT',
        body: JSON.stringify({ symbols: ['BTC/USDT', 'ETH/USDT'] }),
      },
    )
  })

  it('encodes watchlist id in replace path', async () => {
    await replaceWatchlistSymbols('u', 'list/1', ['A'])
    expect(mockedApi).toHaveBeenCalledWith(
      '/users/u/watchlists/list%2F1/symbols',
      expect.any(Object),
    )
  })
})
