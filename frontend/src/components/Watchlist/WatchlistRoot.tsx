import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import { DEFAULT_WATCHLIST_NAME } from '@/constants/watchlist'
import { ApiError } from '@/services/api'
import {
  clearLocalUserId,
  clearStaleUser,
  ensureUserId,
  getErrorCode,
} from '@/services/userBootstrap'
import {
  createWatchlist as createWatchlistApi,
  listWatchlists,
  replaceWatchlistSymbols,
} from '@/services/watchlistApi'
import { readWatchlistCache, writeWatchlistCache } from '@/services/watchlistCache'
import { useWatchlistStore } from '@/stores/watchlistStore'
import type { Watchlist } from '@/types/watchlist'
import type { Symbol } from '@/types/symbol'
import {
  mapWatchlistDto,
  resolveWatchlistDtos,
} from '@/utils/watchlistNormalize'

interface WatchlistSessionValue {
  retry: () => void
  createWatchlist: (name: string) => Promise<Watchlist | null>
  addSymbolToSelected: (symbol: Symbol) => Promise<boolean>
  isAddPending: (watchlistId: string | null) => boolean
}

const WatchlistSessionContext = createContext<WatchlistSessionValue | null>(null)

export function useWatchlistSession(): WatchlistSessionValue {
  const ctx = useContext(WatchlistSessionContext)
  if (!ctx) {
    return {
      retry: () => {},
      createWatchlist: async () => null,
      addSymbolToSelected: async () => false,
      isAddPending: () => false,
    }
  }
  return ctx
}

const mutationChains = new Map<string, Promise<unknown>>()

function enqueueWatchlistMutation<T>(
  watchlistId: string,
  task: () => Promise<T>,
): Promise<T> {
  const previous = mutationChains.get(watchlistId) ?? Promise.resolve()
  const next = previous.catch(() => undefined).then(task)
  mutationChains.set(
    watchlistId,
    next.then(
      () => undefined,
      () => undefined,
    ),
  )
  return next
}

async function persistConfirmedSnapshot(): Promise<void> {
  const state = useWatchlistStore.getState()
  if (!state.userId || state.stale) {
    return
  }
  await writeWatchlistCache({
    version: 1,
    userId: state.userId,
    selectedWatchlistId: state.selectedWatchlistId,
    watchlists: state.watchlists,
    confirmedAt: new Date().toISOString(),
  })
}

async function loadCanonicalWatchlists(userId: string): Promise<Watchlist[]> {
  const dtos = await listWatchlists(userId)
  if (dtos.length === 0) {
    const created = await createWatchlistApi(userId, DEFAULT_WATCHLIST_NAME, [])
    return resolveWatchlistDtos([created])
  }
  return resolveWatchlistDtos(dtos)
}

export function WatchlistRoot({ children }: { children: ReactNode }) {
  const [reloadToken, setReloadToken] = useState(0)
  const staleRecoveryUsedRef = useRef(false)
  const generationRef = useRef(0)

  const pendingWatchlistIds = useWatchlistStore((state) => state.pendingWatchlistIds)

  useEffect(() => {
    const generation = ++generationRef.current
    let cancelled = false

    async function bootstrap() {
      const store = useWatchlistStore.getState()
      store.setBootstrapping()

      try {
        const userId = await ensureUserId()
        if (cancelled || generation !== generationRef.current) {
          return
        }

        useWatchlistStore.getState().setUserId(userId)

        const cache = await readWatchlistCache(userId)
        if (cancelled || generation !== generationRef.current) {
          return
        }

        if (cache) {
          useWatchlistStore.getState().hydrateFromCache({
            userId: cache.userId,
            watchlists: cache.watchlists,
            selectedWatchlistId: cache.selectedWatchlistId,
          })
        }

        useWatchlistStore.getState().beginRefresh()

        try {
          const preferredSelectedId =
            useWatchlistStore.getState().selectedWatchlistId ??
            cache?.selectedWatchlistId ??
            null
          const watchlists = await loadCanonicalWatchlists(userId)
          if (cancelled || generation !== generationRef.current) {
            return
          }

          useWatchlistStore
            .getState()
            .applyCanonical(watchlists, preferredSelectedId)
          await persistConfirmedSnapshot()
          staleRecoveryUsedRef.current = false
        } catch (error) {
          if (cancelled || generation !== generationRef.current) {
            return
          }

          const isUserMissing =
            error instanceof ApiError &&
            error.status === 404 &&
            getErrorCode(error) === 'USER_NOT_FOUND'

          if (isUserMissing) {
            if (staleRecoveryUsedRef.current) {
              useWatchlistStore
                .getState()
                .setError('Stored user is invalid. Clear site data and reload.')
              return
            }
            staleRecoveryUsedRef.current = true
            await clearStaleUser(userId)
            clearLocalUserId()
            setReloadToken((token) => token + 1)
            return
          }

          const message =
            error instanceof Error ? error.message : 'Failed to load watchlists'
          const hasCache = useWatchlistStore.getState().watchlists.length > 0
          useWatchlistStore.getState().setError(message, { keepRows: hasCache })
        }
      } catch (error) {
        if (cancelled || generation !== generationRef.current) {
          return
        }
        const message =
          error instanceof Error ? error.message : 'Failed to bootstrap user'
        useWatchlistStore.getState().setError(message)
      }
    }

    void bootstrap()

    return () => {
      cancelled = true
    }
  }, [reloadToken])

  async function createWatchlist(name: string): Promise<Watchlist | null> {
    const trimmed = name.trim()
    if (!trimmed) {
      return null
    }

    const { userId } = useWatchlistStore.getState()
    if (!userId) {
      return null
    }

    const dto = await createWatchlistApi(userId, trimmed, [])
    let resolved: Watchlist | undefined
    try {
      ;[resolved] = await resolveWatchlistDtos([dto])
    } catch {
      resolved = mapWatchlistDto(dto, [])
    }
    if (!resolved) {
      throw new Error('Failed to resolve created watchlist')
    }
    useWatchlistStore.getState().appendWatchlist(resolved)
    await persistConfirmedSnapshot()
    return resolved
  }

  async function addSymbolToSelected(symbol: Symbol): Promise<boolean> {
    const state = useWatchlistStore.getState()
    const { userId, selectedWatchlistId } = state
    if (!userId || !selectedWatchlistId) {
      return false
    }

    if (state.hasSymbol(selectedWatchlistId, symbol.id)) {
      return false
    }

    const targetId = selectedWatchlistId
    const started = useWatchlistStore
      .getState()
      .beginOptimisticAdd(targetId, symbol)
    if (!started) {
      return false
    }

    return enqueueWatchlistMutation(targetId, async () => {
      let putSucceeded = false
      try {
        const current = useWatchlistStore
          .getState()
          .watchlists.find((list) => list.id === targetId)
        if (!current) {
          useWatchlistStore.getState().rollbackWatchlist(targetId)
          return false
        }

        const dto = await replaceWatchlistSymbols(
          userId,
          targetId,
          current.symbols.map((item) => item.id),
        )
        putSucceeded = true

        let resolved: Watchlist | undefined
        try {
          ;[resolved] = await resolveWatchlistDtos([dto])
        } catch {
          // PUT already committed on the server — keep local symbols in DTO order.
          const byId = new Map(current.symbols.map((item) => [item.id, item]))
          const symbols = dto.symbols.flatMap((id) => {
            const symbol = byId.get(id)
            return symbol ? [symbol] : []
          })
          resolved = mapWatchlistDto(dto, symbols)
        }
        if (!resolved || resolved.symbols.length !== dto.symbols.length) {
          // Still prefer optimistic list over rolling back a confirmed write.
          useWatchlistStore.getState().commitWatchlist(current)
        } else {
          useWatchlistStore.getState().commitWatchlist(resolved)
        }
        // Persist only confirmed non-stale snapshot for the full store.
        const after = useWatchlistStore.getState()
        if (after.userId && !after.stale) {
          await writeWatchlistCache({
            version: 1,
            userId: after.userId,
            selectedWatchlistId: after.selectedWatchlistId,
            watchlists: after.watchlists,
            confirmedAt: new Date().toISOString(),
          })
        }
        return true
      } catch (error) {
        if (!putSucceeded) {
          useWatchlistStore.getState().rollbackWatchlist(targetId)
        }
        throw error
      }
    })
  }

  const value: WatchlistSessionValue = {
    retry: () => {
      staleRecoveryUsedRef.current = false
      useWatchlistStore.getState().clearError()
      setReloadToken((token) => token + 1)
    },
    createWatchlist,
    addSymbolToSelected,
    isAddPending: (watchlistId) =>
      Boolean(watchlistId && pendingWatchlistIds.includes(watchlistId)),
  }

  return (
    <WatchlistSessionContext.Provider value={value}>
      {children}
    </WatchlistSessionContext.Provider>
  )
}
