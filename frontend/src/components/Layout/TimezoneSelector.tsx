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
    <div className="w-full space-y-1">
      <span className="text-[10px] font-semibold uppercase tracking-wider text-text-secondary">
        Timezone
      </span>
      <label className="sr-only" htmlFor="chart-timezone">
        Chart timezone
      </label>
      <select
        id="chart-timezone"
        value={timezone}
        onChange={(event) => setTimezone(event.target.value as ChartTimezoneId)}
        className="w-full cursor-pointer rounded border border-border bg-bg px-2 py-1.5 text-xs text-text outline-none transition-colors hover:border-accent/40"
      >
        {CHART_TIMEZONE_OPTIONS.map((option) => (
          <option key={option.id} value={option.id}>
            {`${option.label} (${offsetLabelFor(option.id)})`}
          </option>
        ))}
      </select>
      <span className="text-[10px] text-text-secondary">{offsetLabel}</span>
    </div>
  )
}

function offsetLabelFor(id: ChartTimezoneId): string {
  return formatTimezoneOffsetLabel(resolveChartTimeZone(id))
}
