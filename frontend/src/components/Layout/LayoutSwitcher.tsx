import {
  LAYOUT_PRESET_LABELS,
  LAYOUT_PRESET_ORDER,
} from '@/constants/workspace'
import type { LayoutPreset } from '@/types/workspace'
import { useWorkspaceStore } from '@/stores/workspaceStore'

export function LayoutSwitcher() {
  const layouts = useWorkspaceStore((s) => s.layouts)
  const activeLayoutId = useWorkspaceStore((s) => s.activeLayoutId)
  const setLayoutPreset = useWorkspaceStore((s) => s.setLayoutPreset)
  const active =
    layouts.find((layout) => layout.id === activeLayoutId)?.preset ?? '1x1'

  return (
    <div
      className="flex shrink-0 items-center gap-1"
      role="group"
      aria-label="Chart layout"
    >
      {LAYOUT_PRESET_ORDER.map((preset: LayoutPreset) => {
        const selected = active === preset
        return (
          <button
            key={preset}
            type="button"
            aria-pressed={selected}
            title={`${LAYOUT_PRESET_LABELS[preset]} (Alt+${LAYOUT_PRESET_ORDER.indexOf(preset) + 1})`}
            onClick={() => setLayoutPreset(preset)}
            className={[
              'rounded border px-2 py-1 text-xs transition-colors',
              selected
                ? 'border-accent/50 bg-accent/15 text-accent'
                : 'border-border text-text-secondary hover:border-accent/40 hover:text-text',
            ].join(' ')}
          >
            {LAYOUT_PRESET_LABELS[preset]}
          </button>
        )
      })}
    </div>
  )
}
