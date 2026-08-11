import { useState } from 'react'
import { useWatchlistSession } from '@/components/Watchlist/WatchlistRoot'
import { WatchlistRow } from '@/components/Watchlist/WatchlistRow'
import { useToast } from '@/components/ui/Toast'
import { writeWatchlistCache } from '@/services/watchlistCache'
import { useWatchlistStore } from '@/stores/watchlistStore'

export function WatchlistPanel() {
  const { retry, createWatchlist } = useWatchlistSession()
  const { showToast } = useToast()

  const watchlists = useWatchlistStore((state) => state.watchlists)
  const selectedWatchlistId = useWatchlistStore((state) => state.selectedWatchlistId)
  const status = useWatchlistStore((state) => state.status)
  const stale = useWatchlistStore((state) => state.stale)
  const errorMessage = useWatchlistStore((state) => state.errorMessage)
  const setSelectedWatchlistId = useWatchlistStore(
    (state) => state.setSelectedWatchlistId,
  )

  const [creating, setCreating] = useState(false)
  const [newName, setNewName] = useState('')
  const [creatingBusy, setCreatingBusy] = useState(false)

  const selected = watchlists.find((list) => list.id === selectedWatchlistId) ?? null
  const showHardError = status === 'error' && watchlists.length === 0
  const showLoading =
    (status === 'bootstrapping' ||
      status === 'hydrating' ||
      status === 'refreshing' ||
      status === 'idle') &&
    watchlists.length === 0 &&
    !errorMessage

  async function persistSelection(nextId: string) {
    setSelectedWatchlistId(nextId)
    const state = useWatchlistStore.getState()
    if (!state.userId || state.stale) {
      return
    }
    await writeWatchlistCache({
      version: 1,
      userId: state.userId,
      selectedWatchlistId: nextId,
      watchlists: state.watchlists,
      confirmedAt: new Date().toISOString(),
    })
  }
  async function handleCreate() {
    const trimmed = newName.trim()
    if (!trimmed || creatingBusy) {
      return
    }
    setCreatingBusy(true)
    try {
      await createWatchlist(trimmed)
      setCreating(false)
      setNewName('')
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Failed to create watchlist'
      showToast(message)
    } finally {
      setCreatingBusy(false)
    }
  }

  return (
    <section
      className="flex min-h-0 flex-1 flex-col border-t border-border"
      aria-label="Watchlist"
    >
      <div className="flex items-center justify-between gap-2 px-3 py-2">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
          Watchlist
        </h2>
        {!creating ? (
          <button
            type="button"
            className="rounded px-1.5 py-0.5 text-xs text-accent hover:bg-bg"
            onClick={() => setCreating(true)}
          >
            New
          </button>
        ) : null}
      </div>

      {creating ? (
        <div className="flex flex-col gap-2 px-3 pb-2">
          <label className="sr-only" htmlFor="new-watchlist-name">
            New watchlist name
          </label>
          <input
            id="new-watchlist-name"
            value={newName}
            onChange={(event) => setNewName(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                void handleCreate()
              }
              if (event.key === 'Escape') {
                setCreating(false)
                setNewName('')
              }
            }}
            placeholder="List name"
            className="w-full rounded border border-border bg-bg px-2 py-1 text-sm text-text outline-none ring-accent focus:ring-1"
            autoFocus
          />
          <div className="flex gap-2">
            <button
              type="button"
              className="rounded bg-accent/15 px-2 py-1 text-xs text-accent disabled:opacity-50"
              disabled={creatingBusy || !newName.trim()}
              onClick={() => void handleCreate()}
            >
              Create
            </button>
            <button
              type="button"
              className="rounded px-2 py-1 text-xs text-text-secondary hover:text-text"
              disabled={creatingBusy}
              onClick={() => {
                setCreating(false)
                setNewName('')
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      ) : null}

      {watchlists.length > 0 ? (
        <div className="px-3 pb-2">
          <label className="sr-only" htmlFor="watchlist-selector">
            Selected watchlist
          </label>
          <select
            id="watchlist-selector"
            value={selectedWatchlistId ?? ''}
            onChange={(event) => {
              void persistSelection(event.target.value)
            }}
            className="w-full rounded border border-border bg-bg px-2 py-1 text-sm text-text outline-none ring-accent focus:ring-1"
          >
            {watchlists.map((list) => (
              <option key={list.id} value={list.id}>
                {list.name}
              </option>
            ))}
          </select>
        </div>
      ) : null}

      {stale &&
      watchlists.length > 0 &&
      (status === 'refreshing' || status === 'hydrating') ? (
        <p className="px-3 pb-1 text-xs text-amber-600 dark:text-amber-400" role="status">
          Showing cached watchlist — refreshing…
        </p>
      ) : null}

      {errorMessage && watchlists.length > 0 ? (
        <div className="flex items-start justify-between gap-2 px-3 pb-1">
          <p className="text-xs text-red-500" role="status">
            {errorMessage}
          </p>
          <button
            type="button"
            className="shrink-0 rounded px-1.5 py-0.5 text-xs text-text-secondary hover:text-text"
            onClick={retry}
          >
            Retry
          </button>
        </div>
      ) : null}

      <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-2">
        {showLoading ? (
          <p className="px-1 py-2 text-xs text-text-secondary" role="status">
            Loading watchlists…
          </p>
        ) : null}

        {showHardError ? (
          <div className="flex flex-col gap-2 px-1 py-2">
            <p className="text-xs text-red-500" role="alert">
              {errorMessage}
            </p>
            <button
              type="button"
              className="self-start rounded border border-border px-2 py-1 text-xs text-text-secondary hover:text-text"
              onClick={retry}
            >
              Retry
            </button>
          </div>
        ) : null}

        {!showLoading && !showHardError && selected && selected.symbols.length === 0 ? (
          <p className="px-1 py-2 text-xs text-text-secondary" role="status">
            No symbols yet. Add from search.
          </p>
        ) : null}

        {selected?.symbols.map((symbol) => (
          <WatchlistRow key={symbol.id} symbol={symbol} />
        ))}
      </div>
    </section>
  )
}
