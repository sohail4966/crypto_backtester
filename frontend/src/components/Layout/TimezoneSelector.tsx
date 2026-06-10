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

interface TimezoneSelectorProps {
  layout?: 'topbar' | 'sidebar'
}

export function TimezoneSelector({ layout = 'topbar' }: TimezoneSelectorProps) {
  const timezone = useChartStore((state) => state.timezone)
  const setTimezone = useChartStore((state) => state.setTimezone)

  const resolvedZone = resolveChartTimeZone(timezone)
  const offsetLabel = useMemo(
    () => formatTimezoneOffsetLabel(resolvedZone),
    [resolvedZone],
  )

  const selectClass =
    layout === 'sidebar'
      ? 'w-full cursor-pointer rounded border border-border bg-bg px-2 py-1.5 text-xs text-text outline-none transition-colors hover:border-accent/40'
      : 'cursor-pointer rounded border border-border bg-bg px-2 py-1 text-xs text-text outline-none transition-colors hover:border-accent/40'

  return (
    <div className={layout === 'sidebar' ? 'w-full space-y-1' : 'flex items-center gap-2 text-xs'}>
      {layout === 'sidebar' ? (
        <span className="text-[10px] font-semibold uppercase tracking-wider text-text-secondary">
          Timezone
        </span>
      ) : (
        <span className="hidden text-text-secondary md:inline">{offsetLabel}</span>
      )}
      <label className="sr-only" htmlFor="chart-timezone">
        Chart timezone
      </label>
      <select
        id="chart-timezone"
        value={timezone}
        onChange={(event) => setTimezone(event.target.value as ChartTimezoneId)}
        className={selectClass}
      >
        {CHART_TIMEZONE_OPTIONS.map((option) => (
          <option key={option.id} value={option.id}>
            {layout === 'sidebar' ? `${option.label} (${offsetLabelFor(option.id)})` : option.label}
          </option>
        ))}
      </select>
      {layout === 'sidebar' ? (
        <span className="text-[10px] text-text-secondary">{offsetLabel}</span>
      ) : null}
    </div>
  )
}

function offsetLabelFor(id: ChartTimezoneId): string {
  return formatTimezoneOffsetLabel(resolveChartTimeZone(id))
}
