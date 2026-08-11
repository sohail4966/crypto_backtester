import { create } from 'zustand'
import type { Watchlist, WatchlistLoadStatus } from '@/types/watchlist'
import type { Symbol } from '@/types/symbol'
import { selectWatchlistId } from '@/utils/watchlistNormalize'

interface WatchlistState {
  userId: string | null
  watchlists: Watchlist[]
  selectedWatchlistId: string | null
  status: WatchlistLoadStatus
  stale: boolean
  errorMessage: string | null
  /** Watchlist IDs with an in-flight Add mutation. */
  pendingWatchlistIds: string[]
  /** Confirmed snapshots captured at optimistic-add start, keyed by list ID. */
  mutationSnapshots: Record<string, Watchlist>

  reset: () => void
  setBootstrapping: () => void
  setUserId: (userId: string) => void
  hydrateFromCache: (args: {
    userId: string
    watchlists: Watchlist[]
    selectedWatchlistId: string | null
  }) => void
  beginRefresh: () => void
  applyCanonical: (
    watchlists: Watchlist[],
    preferredSelectedId: string | null,
  ) => void
  setSelectedWatchlistId: (id: string) => void
  setError: (message: string, options?: { keepRows?: boolean }) => void
  clearError: () => void
  setStale: (stale: boolean) => void
  hasSymbol: (watchlistId: string, symbolId: string) => boolean
  beginOptimisticAdd: (watchlistId: string, symbol: Symbol) => boolean
  markPending: (watchlistId: string, pending: boolean) => void
  commitWatchlist: (watchlist: Watchlist) => void
  rollbackWatchlist: (watchlistId: string) => void
  appendWatchlist: (watchlist: Watchlist) => void
}

const initialState = {
  userId: null as string | null,
  watchlists: [] as Watchlist[],
  selectedWatchlistId: null as string | null,
  status: 'idle' as WatchlistLoadStatus,
  stale: false,
  errorMessage: null as string | null,
  pendingWatchlistIds: [] as string[],
  mutationSnapshots: {} as Record<string, Watchlist>,
}

export const useWatchlistStore = create<WatchlistState>((set, get) => ({
  ...initialState,

  reset: () => set({ ...initialState }),

  setBootstrapping: () =>
    set({
      status: 'bootstrapping',
      errorMessage: null,
    }),

  setUserId: (userId) => set({ userId }),

  hydrateFromCache: ({ userId, watchlists, selectedWatchlistId }) =>
    set({
      userId,
      watchlists,
      selectedWatchlistId: selectWatchlistId(watchlists, selectedWatchlistId),
      status: 'hydrating',
      stale: true,
      errorMessage: null,
    }),

  beginRefresh: () =>
    set((state) => ({
      status: state.watchlists.length > 0 ? 'refreshing' : 'refreshing',
      stale: state.watchlists.length > 0 ? true : state.stale,
      errorMessage: null,
    })),

  applyCanonical: (watchlists, preferredSelectedId) =>
    set((state) => ({
      watchlists,
      selectedWatchlistId: selectWatchlistId(
        watchlists,
        preferredSelectedId ?? state.selectedWatchlistId,
      ),
      status: 'ready',
      stale: false,
      errorMessage: null,
      mutationSnapshots: {},
      pendingWatchlistIds: [],
    })),

  setSelectedWatchlistId: (id) => set({ selectedWatchlistId: id }),

  setError: (message, options) =>
    set((state) => ({
      status: options?.keepRows && state.watchlists.length > 0 ? 'ready' : 'error',
      stale: options?.keepRows && state.watchlists.length > 0 ? true : state.stale,
      errorMessage: message,
    })),

  clearError: () => set({ errorMessage: null }),

  setStale: (stale) => set({ stale }),

  hasSymbol: (watchlistId, symbolId) => {
    const list = get().watchlists.find((item) => item.id === watchlistId)
    return Boolean(list?.symbols.some((symbol) => symbol.id === symbolId))
  },

  beginOptimisticAdd: (watchlistId, symbol) => {
    const state = get()
    const list = state.watchlists.find((item) => item.id === watchlistId)
    if (!list) {
      return false
    }
    if (list.symbols.some((item) => item.id === symbol.id)) {
      return false
    }

    const snapshot: Watchlist = {
      ...list,
      symbols: [...list.symbols],
    }

    set({
      mutationSnapshots: {
        ...state.mutationSnapshots,
        [watchlistId]: snapshot,
      },
      watchlists: state.watchlists.map((item) =>
        item.id === watchlistId
          ? { ...item, symbols: [...item.symbols, symbol] }
          : item,
      ),
      pendingWatchlistIds: state.pendingWatchlistIds.includes(watchlistId)
        ? state.pendingWatchlistIds
        : [...state.pendingWatchlistIds, watchlistId],
    })
    return true
  },

  markPending: (watchlistId, pending) =>
    set((state) => {
      const without = state.pendingWatchlistIds.filter((id) => id !== watchlistId)
      return {
        pendingWatchlistIds: pending ? [...without, watchlistId] : without,
      }
    }),

  commitWatchlist: (watchlist) =>
    set((state) => {
      const { [watchlist.id]: _removed, ...restSnapshots } = state.mutationSnapshots
      return {
        watchlists: state.watchlists.map((item) =>
          item.id === watchlist.id ? watchlist : item,
        ),
        mutationSnapshots: restSnapshots,
        pendingWatchlistIds: state.pendingWatchlistIds.filter(
          (id) => id !== watchlist.id,
        ),
      }
    }),

  rollbackWatchlist: (watchlistId) =>
    set((state) => {
      const snapshot = state.mutationSnapshots[watchlistId]
      const { [watchlistId]: _removed, ...restSnapshots } = state.mutationSnapshots
      if (!snapshot) {
        return {
          mutationSnapshots: restSnapshots,
          pendingWatchlistIds: state.pendingWatchlistIds.filter(
            (id) => id !== watchlistId,
          ),
        }
      }
      return {
        watchlists: state.watchlists.map((item) =>
          item.id === watchlistId ? snapshot : item,
        ),
        mutationSnapshots: restSnapshots,
        pendingWatchlistIds: state.pendingWatchlistIds.filter(
          (id) => id !== watchlistId,
        ),
      }
    }),

  appendWatchlist: (watchlist) =>
    set((state) => ({
      watchlists: [...state.watchlists, watchlist],
      selectedWatchlistId: watchlist.id,
      status: 'ready',
      stale: false,
      errorMessage: null,
    })),
}))
