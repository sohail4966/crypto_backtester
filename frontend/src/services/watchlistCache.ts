import { get as idbGet, set as idbSet, del as idbDel } from 'idb-keyval'
import { WATCHLIST_CACHE_VERSION, watchlistCacheKey } from '@/constants/watchlist'
import type { Watchlist, WatchlistCacheV1 } from '@/types/watchlist'
import type { Symbol } from '@/types/symbol'

const ASSET_TYPES: ReadonlySet<string> = new Set(['spot', 'perp', 'futures'])

function isSymbol(value: unknown): value is Symbol {
  if (!value || typeof value !== 'object') {
    return false
  }
  const row = value as Record<string, unknown>
  return (
    typeof row.id === 'string' &&
    typeof row.ticker === 'string' &&
    typeof row.exchange === 'string' &&
    typeof row.baseAsset === 'string' &&
    typeof row.quoteAsset === 'string' &&
    typeof row.tickSize === 'number' &&
    typeof row.lotSize === 'number' &&
    typeof row.type === 'string' &&
    ASSET_TYPES.has(row.type) &&
    typeof row.active === 'boolean' &&
    typeof row.sortOrder === 'number'
  )
}

function isWatchlist(value: unknown): value is Watchlist {
  if (!value || typeof value !== 'object') {
    return false
  }
  const row = value as Record<string, unknown>
  if (
    typeof row.id !== 'string' ||
    typeof row.userId !== 'string' ||
    typeof row.name !== 'string' ||
    typeof row.isDefault !== 'boolean' ||
    typeof row.sortOrder !== 'number' ||
    typeof row.createdAt !== 'string' ||
    !Array.isArray(row.symbols)
  ) {
    return false
  }
  return row.symbols.every(isSymbol)
}

export function isValidWatchlistCache(
  value: unknown,
  expectedUserId: string,
): value is WatchlistCacheV1 {
  if (!value || typeof value !== 'object') {
    return false
  }
  const row = value as Record<string, unknown>
  if (row.version !== WATCHLIST_CACHE_VERSION) {
    return false
  }
  if (row.userId !== expectedUserId || typeof row.userId !== 'string') {
    return false
  }
  if (
    row.selectedWatchlistId !== null &&
    typeof row.selectedWatchlistId !== 'string'
  ) {
    return false
  }
  if (typeof row.confirmedAt !== 'string') {
    return false
  }
  if (!Array.isArray(row.watchlists)) {
    return false
  }
  return row.watchlists.every(isWatchlist)
}

export async function readWatchlistCache(
  userId: string,
): Promise<WatchlistCacheV1 | null> {
  const key = watchlistCacheKey(userId)
  const raw = await idbGet(key)
  if (raw == null) {
    return null
  }
  if (!isValidWatchlistCache(raw, userId)) {
    await idbDel(key)
    return null
  }
  return raw
}

export async function writeWatchlistCache(cache: WatchlistCacheV1): Promise<void> {
  if (!isValidWatchlistCache(cache, cache.userId)) {
    throw new Error('Refusing to persist invalid watchlist cache')
  }
  await idbSet(watchlistCacheKey(cache.userId), cache)
}

export async function deleteWatchlistCache(userId: string): Promise<void> {
  await idbDel(watchlistCacheKey(userId))
}
