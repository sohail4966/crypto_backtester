import { ChartZoomControls } from '@/components/Chart/ChartZoomControls'

interface ChartToolbarProps {
  barCount: number
}

export function ChartToolbar({ barCount }: ChartToolbarProps) {
  return (
    <div className="absolute right-3 top-3 z-20 flex items-center gap-1 rounded border border-border bg-surface/90 p-0.5 shadow-sm backdrop-blur-sm">
      <ChartZoomControls barCount={barCount} embedded />
    </div>
  )
}
