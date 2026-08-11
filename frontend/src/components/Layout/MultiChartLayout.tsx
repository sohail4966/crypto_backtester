import type { CSSProperties } from 'react'
import { ChartContainer } from '@/components/Chart/ChartContainer'
import type { LayoutPreset } from '@/types/workspace'
import { useWorkspaceStore } from '@/stores/workspaceStore'

function gridClassForPreset(preset: LayoutPreset): string {
  switch (preset) {
    case '1x1':
      return 'grid-cols-1 grid-rows-1'
    case '1x2':
      return 'grid-cols-2 grid-rows-1'
    case '2x2':
      return 'grid-cols-2 grid-rows-2'
    case '1plus2':
      return 'grid-cols-2 grid-rows-2'
    default:
      return 'grid-cols-1 grid-rows-1'
  }
}

function paneStyle(
  preset: LayoutPreset,
  index: number,
): CSSProperties | undefined {
  if (preset !== '1plus2') {
    return undefined
  }
  if (index === 0) {
    return { gridColumn: 1, gridRow: '1 / span 2' }
  }
  if (index === 1) {
    return { gridColumn: 2, gridRow: 1 }
  }
  return { gridColumn: 2, gridRow: 2 }
}

export function MultiChartLayout() {
  const layouts = useWorkspaceStore((s) => s.layouts)
  const activeLayoutId = useWorkspaceStore((s) => s.activeLayoutId)
  const activePaneId = useWorkspaceStore((s) => s.activePaneId)
  const setActivePaneId = useWorkspaceStore((s) => s.setActivePaneId)

  const layout =
    layouts.find((item) => item.id === activeLayoutId) ?? layouts[0]
  const preset = layout?.preset ?? '1x1'
  const panes = layout?.panes ?? []

  return (
    <div
      className={`grid h-full min-h-0 w-full gap-1 ${gridClassForPreset(preset)}`}
      data-layout-preset={preset}
      data-testid="multi-chart-layout"
    >
      {panes.map((pane, index) => {
        const isActive = pane.id === activePaneId
        return (
          <div
            key={pane.id}
            style={paneStyle(preset, index)}
            className={[
              'relative min-h-0 min-w-0 overflow-hidden rounded border',
              isActive ? 'border-accent/60' : 'border-border',
            ].join(' ')}
            onMouseDown={() => setActivePaneId(pane.id)}
          >
            <ChartContainer
              paneId={pane.id}
              isActive={isActive}
              symbolOverride={pane.symbol}
              timeframeOverride={pane.timeframe}
              className="relative h-full min-h-0 w-full flex-1"
              onActivate={() => setActivePaneId(pane.id)}
            />
          </div>
        )
      })}
    </div>
  )
}
