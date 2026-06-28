import { useState } from 'react'
import { IndicatorPanel } from '@/components/Indicators/IndicatorPanel'

export function IndicatorsBar() {
  const [pickerOpen, setPickerOpen] = useState(false)

  return (
    <div className="flex shrink-0 items-center gap-2 border-l border-border pl-4">
      <span className="shrink-0 text-xs font-semibold uppercase tracking-wider text-text-secondary">
        Indicators
      </span>

      <div className="relative shrink-0">
        <button
          type="button"
          onClick={() => setPickerOpen((prev) => !prev)}
          className="rounded border border-border px-2.5 py-1 text-xs text-text transition-colors hover:border-accent/40 hover:text-accent"
        >
          + Add indicator
        </button>
        <IndicatorPanel open={pickerOpen} onClose={() => setPickerOpen(false)} />
      </div>
    </div>
  )
}
