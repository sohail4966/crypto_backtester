import { apiRequest } from '@/services/api'
import type { WatchlistDto } from '@/types/watchlist'

export function listWatchlists(userId: string): Promise<WatchlistDto[]> {
  return apiRequest<WatchlistDto[]>(
    `/users/${encodeURIComponent(userId)}/watchlists`,
  )
}

export function createWatchlist(
  userId: string,
  name: string,
  symbols: string[] = [],
): Promise<WatchlistDto> {
  return apiRequest<WatchlistDto>(
    `/users/${encodeURIComponent(userId)}/watchlists`,
    {
      method: 'POST',
      body: JSON.stringify({ name, symbols }),
    },
  )
}

export function replaceWatchlistSymbols(
  userId: string,
  watchlistId: string,
  symbols: string[],
): Promise<WatchlistDto> {
  return apiRequest<WatchlistDto>(
    `/users/${encodeURIComponent(userId)}/watchlists/${encodeURIComponent(watchlistId)}/symbols`,
    {
      method: 'PUT',
      body: JSON.stringify({ symbols }),
    },
  )
}
