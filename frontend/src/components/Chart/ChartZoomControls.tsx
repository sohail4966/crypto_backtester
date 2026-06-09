import { useChartContext } from '@/components/Chart/ChartContext'
import { useChartZoom } from '@/hooks/useChartZoom'

interface ChartZoomControlsProps {
  barCount: number
  /** Render inside ChartToolbar without its own positioned wrapper. */
  embedded?: boolean
}

export function ChartZoomControls({ barCount, embedded = false }: ChartZoomControlsProps) {
  const { chart } = useChartContext()
  const { zoomIn, zoomOut, resetZoom } = useChartZoom(chart, barCount)

  const controls = (
    <>
      <button
        type="button"
        aria-label="Zoom out"
        onClick={zoomOut}
        className="rounded px-2 py-1 text-sm text-text-secondary transition-colors hover:bg-bg hover:text-text"
      >
        −
      </button>
      <button
        type="button"
        aria-label="Reset zoom"
        onClick={resetZoom}
        className="rounded px-2 py-1 text-xs text-text-secondary transition-colors hover:bg-bg hover:text-text"
      >
        Fit
      </button>
      <button
        type="button"
        aria-label="Zoom in"
        onClick={zoomIn}
        className="rounded px-2 py-1 text-sm text-text-secondary transition-colors hover:bg-bg hover:text-text"
      >
        +
      </button>
    </>
  )

  if (embedded) {
    return <div className="flex items-center gap-1">{controls}</div>
  }

  return (
    <div className="absolute right-3 top-3 z-20 flex items-center gap-1 rounded border border-border bg-surface/90 p-0.5 shadow-sm backdrop-blur-sm">
      {controls}
    </div>
  )
}
