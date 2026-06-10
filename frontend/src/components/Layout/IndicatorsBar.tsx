import { useMemo, useState } from 'react'
import { IndicatorPanel } from '@/components/Indicators/IndicatorPanel'
import { IndicatorTab } from '@/components/Indicators/IndicatorTab'
import { useIndicatorStore } from '@/stores/indicatorStore'
import { indicatorTabEntries } from '@/utils/indicatorCatalog'

export function IndicatorsBar() {
  const [pickerOpen, setPickerOpen] = useState(false)
  const active = useIndicatorStore((state) => state.active)
  const remove = useIndicatorStore((state) => state.remove)
  const toggleVisible = useIndicatorStore((state) => state.toggleVisible)
  const openSettings = useIndicatorStore((state) => state.openSettings)

  const tabs = useMemo(() => indicatorTabEntries(active), [active])

  return (
    <div className="flex min-w-0 flex-1 items-center gap-2 border-l border-border pl-4">
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

      <div className="flex min-w-0 flex-1 flex-wrap items-center gap-1.5 overflow-x-auto">
        {tabs.map((tab) => (
          <IndicatorTab
            key={tab.instanceId}
            label={tab.label}
            visible={tab.visible}
            hasSettings={tab.hasSettings}
            onToggleVisible={() => toggleVisible(tab.instanceId)}
            onOpenSettings={
              tab.hasSettings ? () => openSettings(tab.instanceId) : undefined
            }
            onRemove={() => remove(tab.instanceId)}
            compact
          />
        ))}
      </div>
    </div>
  )
}
