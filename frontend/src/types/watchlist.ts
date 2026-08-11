import type { Symbol } from '@/types/symbol'

/** Backend user record (JSON UUIDs as strings). */
export interface UserResponse {
  id: string
  name: string
  email: string
  created_at: string
  updated_at?: string
}

/** Backend watchlist DTO — symbols are ordered ID strings. */
export interface WatchlistDto {
  id: string
  user_id: string
  name: string
  is_default: boolean
  sort_order: number
  symbols: string[]
  created_at: string
}

/** Frontend domain watchlist with resolved Symbol entities. */
export interface Watchlist {
  id: string
  userId: string
  name: string
  isDefault: boolean
  sortOrder: number
  symbols: Symbol[]
  createdAt: string
}

export interface WatchlistCacheV1 {
  version: 1
  userId: string
  selectedWatchlistId: string | null
  watchlists: Watchlist[]
  confirmedAt: string
}

export type WatchlistLoadStatus =
  | 'idle'
  | 'bootstrapping'
  | 'hydrating'
  | 'refreshing'
  | 'ready'
  | 'error'
