import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useWatchlistSession } from '@/components/Watchlist/WatchlistRoot'
import { useToast } from '@/components/ui/Toast'
import { searchSymbols } from '@/services/chartDataAdapter'
import { useChartStore } from '@/stores/chartStore'
import { useWatchlistStore } from '@/stores/watchlistStore'
import type { Symbol } from '@/types/symbol'

function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value)

  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delayMs)
    return () => window.clearTimeout(timer)
  }, [delayMs, value])

  return debounced
}

export function SymbolSearch() {
  const symbol = useChartStore((state) => state.symbol)
  const setSymbol = useChartStore((state) => state.setSymbol)
  const selectedWatchlistId = useWatchlistStore((state) => state.selectedWatchlistId)
  const selectedWatchlist = useWatchlistStore((state) =>
    state.watchlists.find((list) => list.id === state.selectedWatchlistId) ?? null,
  )
  const hasSymbol = useWatchlistStore((state) => state.hasSymbol)
  const { addSymbolToSelected, isAddPending } = useWatchlistSession()
  const { showToast } = useToast()

  const [query, setQuery] = useState(symbol?.ticker ?? '')
  const [open, setOpen] = useState(false)
  const trimmedQuery = query.trim()
  const debouncedQuery = useDebouncedValue(trimmedQuery, 250)
  const addPending = isAddPending(selectedWatchlistId)

  const resultsQuery = useQuery({
    queryKey: ['symbols', 'search', debouncedQuery],
    queryFn: () => searchSymbols(debouncedQuery),
    enabled: open,
    staleTime: 30_000,
  })

  useEffect(() => {
    if (symbol?.ticker) {
      setQuery(symbol.ticker)
    }
  }, [symbol?.ticker])

  function selectSymbol(next: Symbol) {
    setSymbol(next)
    setQuery(next.ticker)
    setOpen(false)
  }

  async function handleAdd(item: Symbol) {
    if (!selectedWatchlistId || !selectedWatchlist) {
      showToast('Select a watchlist before adding symbols')
      return
    }
    if (hasSymbol(selectedWatchlistId, item.id)) {
      return
    }

    try {
      await addSymbolToSelected(item)
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Failed to add symbol'
      showToast(message)
    }
  }

  const showResults = open
  const listName = selectedWatchlist?.name ?? 'watchlist'

  return (
    <div className="relative w-full max-w-xs">
      <input
        type="search"
        value={query}
        onChange={(event) => {
          setQuery(event.target.value)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => {
          window.setTimeout(() => setOpen(false), 150)
        }}
        placeholder="Search symbols…"
        className="w-full rounded border border-border bg-bg px-3 py-1.5 text-sm text-text outline-none ring-accent focus:ring-1"
        aria-label="Search symbols"
        aria-expanded={open}
        aria-controls="symbol-search-results"
      />

      {showResults ? (
        <div
          id="symbol-search-results"
          className="absolute z-20 mt-1 max-h-56 w-full overflow-auto rounded border border-border bg-surface py-1 shadow-lg"
          role="listbox"
        >
          {resultsQuery.isFetching ? (
            <p className="px-3 py-2 text-xs text-text-secondary" role="status">
              Searching…
            </p>
          ) : null}

          {resultsQuery.isError ? (
            <p className="px-3 py-2 text-xs text-red-500" role="alert">
              {resultsQuery.error instanceof Error
                ? resultsQuery.error.message
                : 'Search failed'}
            </p>
          ) : null}

          {!resultsQuery.isFetching &&
          !resultsQuery.isError &&
          resultsQuery.data &&
          resultsQuery.data.length === 0 ? (
            <p className="px-3 py-2 text-xs text-text-secondary" role="status">
              No symbols found
            </p>
          ) : null}

          {resultsQuery.data && resultsQuery.data.length > 0 ? (
            <ul>
              {resultsQuery.data.map((item) => {
                const alreadyAdded = selectedWatchlistId
                  ? hasSymbol(selectedWatchlistId, item.id)
                  : false
                return (
                  <li key={item.id} className="flex items-stretch">
                    <button
                      type="button"
                      role="option"
                      className="flex min-w-0 flex-1 items-center justify-between gap-2 px-3 py-2 text-left text-sm hover:bg-bg"
                      onMouseDown={(event) => event.preventDefault()}
                      onClick={() => selectSymbol(item)}
                    >
                      <span className="min-w-0 truncate font-medium">{item.ticker}</span>
                      <span className="shrink-0 text-xs text-text-secondary">
                        {item.exchange}
                      </span>
                      <span className="shrink-0 text-xs uppercase text-text-secondary">
                        {item.type}
                      </span>
                    </button>
                    <button
                      type="button"
                      className="shrink-0 border-l border-border px-2 text-xs text-accent hover:bg-bg disabled:cursor-default disabled:text-text-secondary"
                      disabled={alreadyAdded || addPending || !selectedWatchlistId}
                      aria-label={
                        alreadyAdded
                          ? `${item.ticker} already in ${listName}`
                          : `Add ${item.ticker} to ${listName}`
                      }
                      onMouseDown={(event) => {
                        event.preventDefault()
                        event.stopPropagation()
                      }}
                      onClick={(event) => {
                        event.preventDefault()
                        event.stopPropagation()
                        void handleAdd(item)
                      }}
                    >
                      {alreadyAdded ? 'Added' : 'Add'}
                    </button>
                  </li>
                )
              })}
            </ul>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
