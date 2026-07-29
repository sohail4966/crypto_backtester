import { TIMEFRAME_OPTIONS, type ChartTimeframe } from '@/constants/chart'
import { useChartStore } from '@/stores/chartStore'

export function TimeframeSelector() {
  const timeframe = useChartStore((state) => state.timeframe)
  const setTimeframe = useChartStore((state) => state.setTimeframe)

  return (
    <div className="shrink-0">
      <label className="sr-only" htmlFor="chart-timeframe">
        Chart timeframe
      </label>
      <select
        id="chart-timeframe"
        value={timeframe}
        onChange={(event) => setTimeframe(event.target.value as ChartTimeframe)}
        className="cursor-pointer rounded border border-border bg-bg px-2 py-1 text-xs text-text outline-none transition-colors hover:border-accent/40"
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
