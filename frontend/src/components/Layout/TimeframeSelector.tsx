import { TIMEFRAME_OPTIONS } from '@/constants/chart'
import { useChartStore } from '@/stores/chartStore'

export function TimeframeSelector() {
  const timeframe = useChartStore((state) => state.timeframe)
  const setTimeframe = useChartStore((state) => state.setTimeframe)

  return (
    <div className="flex items-center gap-1">
      {TIMEFRAME_OPTIONS.map((option) => {
        const active = option === timeframe
        return (
          <button
            key={option}
            type="button"
            onClick={() => setTimeframe(option)}
            className={[
              'rounded px-2 py-1 text-xs font-medium transition-colors',
              active
                ? 'bg-accent/15 text-accent'
                : 'text-text-secondary hover:bg-bg hover:text-text',
            ].join(' ')}
          >
            {option}
          </button>
        )
      })}
    </div>
  )
}
