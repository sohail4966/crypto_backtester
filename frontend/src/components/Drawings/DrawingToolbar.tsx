import { DRAWING_TOOLS } from '@/constants/drawings'
import { useDrawingStore } from '@/stores/drawingStore'
import type { DrawingType } from '@/types/drawing'

export function DrawingToolbar() {
  const activeTool = useDrawingStore((s) => s.activeTool)
  const setActiveTool = useDrawingStore((s) => s.setActiveTool)
  const clearTool = useDrawingStore((s) => s.clearTool)
  const draft = useDrawingStore((s) => s.draft)

  const toggle = (type: DrawingType) => {
    if (activeTool === type) {
      clearTool()
      return
    }
    setActiveTool(type)
  }

  return (
    <div
      className="flex shrink-0 items-center gap-1 border-l border-border pl-3"
      role="toolbar"
      aria-label="Drawing tools"
    >
      {DRAWING_TOOLS.map((tool) => {
        const active = activeTool === tool.type
        return (
          <button
            key={tool.type}
            type="button"
            title={`${tool.label} (${tool.shortcut})`}
            aria-pressed={active}
            onClick={() => toggle(tool.type)}
            className={[
              'rounded border px-2 py-1 text-xs transition-colors',
              active
                ? 'border-accent bg-accent/15 text-accent'
                : 'border-border text-text-secondary hover:border-accent/40 hover:text-accent',
            ].join(' ')}
          >
            {tool.label}
          </button>
        )
      })}
      {draft ? (
        <span className="ml-1 text-[10px] text-text-secondary">
          {draft.type === 'price_range'
            ? draft.targetPrice == null
              ? 'Click target'
              : 'Click stop'
            : 'Click second point'}
        </span>
      ) : null}
    </div>
  )
}
