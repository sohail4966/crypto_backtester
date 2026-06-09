import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { searchSymbols } from '@/services/chartDataAdapter'
import { useChartStore } from '@/stores/chartStore'
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
  const [query, setQuery] = useState(symbol?.ticker ?? '')
  const [open, setOpen] = useState(false)
  const debouncedQuery = useDebouncedValue(query, 250)

  // Debounce + fetch only while open — avoids hammering /symbols/search on every keystroke.
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
    // Store the full Symbol entity — chart-data and data-range use next.id, not the ticker string.
    setSymbol(next)
    setQuery(next.ticker)
    setOpen(false)
  }

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
      />

      {open && resultsQuery.data && resultsQuery.data.length > 0 ? (
        <ul className="absolute z-20 mt-1 max-h-56 w-full overflow-auto rounded border border-border bg-surface py-1 shadow-lg">
          {resultsQuery.data.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-bg"
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => selectSymbol(item)}
              >
                <span>{item.ticker}</span>
                <span className="text-xs text-text-secondary">{item.exchange}</span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
