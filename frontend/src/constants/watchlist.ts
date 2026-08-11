export const USER_ID_STORAGE_KEY = 'user_id'

export const WATCHLIST_CACHE_VERSION = 1 as const

export const DEV_USER_NAME = 'Dev User'
export const DEV_USER_EMAIL = 'dev@local'

export const DEFAULT_WATCHLIST_NAME = 'Default'

export const USERS_PAGE_SIZE = 500

export const SYMBOL_RESOLVE_CONCURRENCY = 4

export function watchlistCacheKey(userId: string): string {
  return `watchlists:${userId}:v1`
}
