import { useMemo } from 'react'
import {
  CHART_TIMEZONE_OPTIONS,
  type ChartTimezoneId,
} from '@/constants/timezone'
import { useChartStore } from '@/stores/chartStore'
import {
  formatTimezoneOffsetLabel,
  resolveChartTimeZone,
} from '@/utils/chartTimezone'

export function TimezoneSelector() {
  const timezone = useChartStore((state) => state.timezone)
  const setTimezone = useChartStore((state) => state.setTimezone)

  const resolvedZone = resolveChartTimeZone(timezone)
  const offsetLabel = useMemo(
    () => formatTimezoneOffsetLabel(resolvedZone),
    [resolvedZone],
  )

  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="hidden text-text-secondary md:inline">{offsetLabel}</span>
      <label className="sr-only" htmlFor="chart-timezone">
        Chart timezone
      </label>
      <select
        id="chart-timezone"
        value={timezone}
        onChange={(event) => setTimezone(event.target.value as ChartTimezoneId)}
        className="cursor-pointer rounded border border-border bg-bg px-2 py-1 text-xs text-text outline-none transition-colors hover:border-accent/40"
      >
        {CHART_TIMEZONE_OPTIONS.map((option) => (
          <option key={option.id} value={option.id}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  )
}
