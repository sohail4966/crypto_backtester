import { useMemo, useState } from 'react'
import { IndicatorPanel } from '@/components/Indicators/IndicatorPanel'
import { useIndicatorStore } from '@/stores/indicatorStore'
import { isMacdKey } from '@/types/indicator'

function chipLabel(key: string, params: Record<string, unknown>): string {
  if (isMacdKey(key)) {
    return 'MACD'
  }
  const period = params.period
  return period != null ? `${key} ${period}` : key
}

export function IndicatorsBar() {
  const [open, setOpen] = useState(false)
  const active = useIndicatorStore((state) => state.active)
  const remove = useIndicatorStore((state) => state.remove)

  const chips = useMemo(() => {
    const seen = new Set<string>()
    const list: Array<{ instanceId: string; label: string }> = []
    for (const item of active) {
      const label = chipLabel(item.key, item.params)
      const dedupeKey = isMacdKey(item.key)
        ? `MACD:${JSON.stringify(item.params)}`
        : item.seriesId
      if (seen.has(dedupeKey)) {
        continue
      }
      seen.add(dedupeKey)
      list.push({ instanceId: item.instanceId, label })
    }
    return list
  }, [active])

  return (
    <div className="flex min-w-0 flex-1 items-center gap-2 border-l border-border pl-4">
      <span className="shrink-0 text-xs font-semibold uppercase tracking-wider text-text-secondary">
        Indicators
      </span>

      <div className="relative">
        <button
          type="button"
          onClick={() => setOpen((prev) => !prev)}
          className="rounded border border-border px-2.5 py-1 text-xs text-text transition-colors hover:border-accent/40 hover:text-accent"
        >
          + Add indicator
        </button>
        <IndicatorPanel open={open} onClose={() => setOpen(false)} />
      </div>

      <div className="flex min-w-0 flex-1 flex-wrap items-center gap-1.5">
        {chips.map((chip) => (
          <button
            key={chip.instanceId}
            type="button"
            onClick={() => remove(chip.instanceId)}
            className="group flex items-center gap-1 rounded-full border border-border bg-bg px-2 py-0.5 text-xs text-text-secondary transition-colors hover:border-bear/40 hover:text-bear"
            title="Remove indicator"
          >
            <span>{chip.label}</span>
            <span aria-hidden className="text-[10px]">
              ×
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}
