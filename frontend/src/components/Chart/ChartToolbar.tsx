import { ChartSettings } from '@/components/Chart/ChartSettings'
import { ChartZoomControls } from '@/components/Chart/ChartZoomControls'

interface ChartToolbarProps {
  barCount: number
  showGrid: boolean
  onShowGridChange: (show: boolean) => void
}

export function ChartToolbar({
  barCount,
  showGrid,
  onShowGridChange,
}: ChartToolbarProps) {
  return (
    <div className="absolute right-3 top-3 z-20 flex items-center gap-1 rounded border border-border bg-surface/90 p-0.5 shadow-sm backdrop-blur-sm">
      <ChartSettings showGrid={showGrid} onShowGridChange={onShowGridChange} />
      <div className="h-5 w-px bg-border" aria-hidden />
      <ChartZoomControls barCount={barCount} embedded />
    </div>
  )
}
