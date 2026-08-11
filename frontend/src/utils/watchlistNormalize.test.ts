import { describe, expect, it, vi } from 'vitest'
import type { WatchlistDto } from '@/types/watchlist'
import type { Symbol } from '@/types/symbol'
import {
  mapWatchlistDto,
  resolveWatchlistDtos,
  selectWatchlistId,
  SymbolResolveError,
} from '@/utils/watchlistNormalize'

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

const inactive: Symbol = {
  ...btc,
  id: 'INACTIVE/USDT',
  ticker: 'INACTIVE/USDT',
  baseAsset: 'INACTIVE',
  active: false,
  sortOrder: 99,
}

function dto(overrides: Partial<WatchlistDto> = {}): WatchlistDto {
  return {
    id: 'wl-1',
    user_id: 'user-1',
    name: 'Default',
    is_default: true,
    sort_order: 0,
    symbols: ['BTC/USDT', 'ETH/USDT'],
    created_at: '2024-01-01T00:00:00Z',
    ...overrides,
  }
}

describe('watchlistNormalize', () => {
  it('maps snake_case DTO metadata and preserves backend symbol order', async () => {
    const result = await resolveWatchlistDtos([dto()], {
      searchSymbols: async () => [eth, btc],
      getSymbol: async () => {
        throw new Error('should not fallback')
      },
    })

    expect(result[0]).toMatchObject({
      id: 'wl-1',
      userId: 'user-1',
      isDefault: true,
      sortOrder: 0,
    })
    expect(result[0]?.symbols.map((s) => s.id)).toEqual(['BTC/USDT', 'ETH/USDT'])
  })

  it('falls back to getSymbol for catalog misses', async () => {
    const getSymbol = vi.fn(async (id: string) => {
      if (id === inactive.id) {
        return inactive
      }
      throw new Error('missing')
    })

    const result = await resolveWatchlistDtos(
      [dto({ symbols: ['BTC/USDT', 'INACTIVE/USDT'] })],
      {
        searchSymbols: async () => [btc],
        getSymbol,
      },
    )

    expect(getSymbol).toHaveBeenCalledWith('INACTIVE/USDT')
    expect(result[0]?.symbols.map((s) => s.id)).toEqual([
      'BTC/USDT',
      'INACTIVE/USDT',
    ])
  })

  it('fails rather than dropping an unresolved ID', async () => {
    await expect(
      resolveWatchlistDtos([dto({ symbols: ['BTC/USDT', 'MISSING'] })], {
        searchSymbols: async () => [btc],
        getSymbol: async () => {
          throw new Error('404')
        },
      }),
    ).rejects.toBeInstanceOf(SymbolResolveError)
  })

  it('skips catalog fetch when every list has empty symbols', async () => {
    const searchSymbols = vi.fn(async () => [btc])
    const result = await resolveWatchlistDtos(
      [dto({ symbols: [] }), dto({ id: 'wl-2', symbols: [] })],
      {
        searchSymbols,
        getSymbol: async () => {
          throw new Error('should not fallback')
        },
      },
    )

    expect(searchSymbols).not.toHaveBeenCalled()
    expect(result).toHaveLength(2)
    expect(result[0]?.symbols).toEqual([])
    expect(result[1]?.symbols).toEqual([])
  })

  it('selects default, then lowest sortOrder, then response order', () => {
    const lists = [
      mapWatchlistDto(dto({ id: 'a', is_default: false, sort_order: 2 }), []),
      mapWatchlistDto(dto({ id: 'b', is_default: true, sort_order: 5 }), []),
      mapWatchlistDto(dto({ id: 'c', is_default: false, sort_order: 1 }), []),
    ]
    expect(selectWatchlistId(lists, null)).toBe('b')

    const noDefault = [
      mapWatchlistDto(dto({ id: 'x', is_default: false, sort_order: 3 }), []),
      mapWatchlistDto(dto({ id: 'y', is_default: false, sort_order: 1 }), []),
      mapWatchlistDto(dto({ id: 'z', is_default: false, sort_order: 1 }), []),
    ]
    expect(selectWatchlistId(noDefault, null)).toBe('y')
    expect(selectWatchlistId(noDefault, 'z')).toBe('z')
  })
})
