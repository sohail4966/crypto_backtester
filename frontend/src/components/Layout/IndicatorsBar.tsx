import { useState } from 'react'
import { DrawingToolbar } from '@/components/Drawings/DrawingToolbar'
import { IndicatorPanel } from '@/components/Indicators/IndicatorPanel'
import { ReplayToggle } from '@/components/Replay/ReplayToggle'
import { useOptionalReplaySession } from '@/components/Replay/ReplaySessionContext'
import { useChartStore } from '@/stores/chartStore'
import { useReplayStore } from '@/stores/replayStore'

export function IndicatorsBar() {
  const [pickerOpen, setPickerOpen] = useState(false)
  const session = useOptionalReplaySession()
  const setReplayMode = useChartStore((s) => s.setReplayMode)

  const handleToggleOff = () => {
    if (session) {
      void session.teardownFully()
      return
    }
    useReplayStore.getState().reset()
    setReplayMode(false)
  }

  return (
    <div className="flex shrink-0 items-center gap-2 border-l border-border pl-4">
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
      <ReplayToggle onToggleOff={handleToggleOff} />
      <DrawingToolbar />
    </div>
  )
}
