import { apiRequest } from '@/services/api'
import type { WatchlistDto } from '@/types/watchlist'

export function listWatchlists(userId: string): Promise<WatchlistDto[]> {
  return apiRequest<WatchlistDto[]>(
    `/users/${encodeURIComponent(userId)}/watchlists`,
  )
}

export function getWatchlist(
  userId: string,
  watchlistId: string,
): Promise<WatchlistDto> {
  return apiRequest<WatchlistDto>(
    `/users/${encodeURIComponent(userId)}/watchlists/${encodeURIComponent(watchlistId)}`,
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

export function patchWatchlist(
  userId: string,
  watchlistId: string,
  patch: { name?: string; is_default?: boolean },
): Promise<WatchlistDto> {
  return apiRequest<WatchlistDto>(
    `/users/${encodeURIComponent(userId)}/watchlists/${encodeURIComponent(watchlistId)}`,
    {
      method: 'PATCH',
      body: JSON.stringify(patch),
    },
  )
}

export function deleteWatchlist(
  userId: string,
  watchlistId: string,
): Promise<void> {
  return apiRequest<void>(
    `/users/${encodeURIComponent(userId)}/watchlists/${encodeURIComponent(watchlistId)}`,
    { method: 'DELETE' },
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
