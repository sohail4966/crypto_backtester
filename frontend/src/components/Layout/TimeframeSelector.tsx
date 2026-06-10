import { TIMEFRAME_OPTIONS, type ChartTimeframe } from '@/constants/chart'
import { useChartStore } from '@/stores/chartStore'

interface TimeframeSelectorProps {
  layout?: 'topbar' | 'sidebar'
}

export function TimeframeSelector({ layout = 'topbar' }: TimeframeSelectorProps) {
  const timeframe = useChartStore((state) => state.timeframe)
  const setTimeframe = useChartStore((state) => state.setTimeframe)

  const selectClass =
    layout === 'sidebar'
      ? 'w-full cursor-pointer rounded border border-border bg-bg px-2 py-1.5 text-xs text-text outline-none transition-colors hover:border-accent/40'
      : 'cursor-pointer rounded border border-border bg-bg px-2 py-1 text-xs text-text outline-none transition-colors hover:border-accent/40'

  return (
    <div className={layout === 'sidebar' ? 'w-full' : 'shrink-0'}>
      <label className="sr-only" htmlFor="chart-timeframe">
        Chart timeframe
      </label>
      <select
        id="chart-timeframe"
        value={timeframe}
        onChange={(event) => setTimeframe(event.target.value as ChartTimeframe)}
        className={selectClass}
      >
        {TIMEFRAME_OPTIONS.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </div>
  )
}
