import { useChartStore } from '@/stores/chartStore'
import type { Symbol } from '@/types/symbol'

interface WatchlistRowProps {
  symbol: Symbol
}

export function WatchlistRow({ symbol }: WatchlistRowProps) {
  const chartSymbol = useChartStore((state) => state.symbol)
  const setSymbol = useChartStore((state) => state.setSymbol)
  const isActive = chartSymbol?.id === symbol.id

  return (
    <button
      type="button"
      onClick={() => setSymbol(symbol)}
      aria-current={isActive ? 'true' : undefined}
      className={[
        'flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm transition-colors',
        isActive
          ? 'bg-accent/15 text-accent'
          : 'text-text hover:bg-bg',
      ].join(' ')}
    >
      <span className="min-w-0 flex-1 truncate font-medium">{symbol.ticker}</span>
      <span className="shrink-0 text-xs text-text-secondary">{symbol.exchange}</span>
      <span className="w-6 shrink-0 text-right text-xs text-text-secondary" aria-hidden>
        —
      </span>
    </button>
  )
}
