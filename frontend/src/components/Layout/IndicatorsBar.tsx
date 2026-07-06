import { useState } from 'react'
import { IndicatorPanel } from '@/components/Indicators/IndicatorPanel'
import { useChartStore } from '@/stores/chartStore'
import { useReplayStore } from '@/stores/replayStore'

export function IndicatorsBar() {
  const [pickerOpen, setPickerOpen] = useState(false)
  const replayMode = useChartStore((state) => state.replayMode)
  const setReplayMode = useChartStore((state) => state.setReplayMode)
  const phase = useReplayStore((state) => state.phase)

  const toggleReplay = () => {
    const next = !replayMode
    setReplayMode(next)
    if (!next) {
      useReplayStore.getState().setInactive()
    }
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

      <button
        type="button"
        aria-pressed={replayMode}
        onClick={toggleReplay}
        className={[
          'rounded border px-2.5 py-1 text-xs transition-colors',
          replayMode
            ? 'border-accent/50 bg-accent/15 text-accent'
            : 'border-border text-text hover:border-accent/40 hover:text-accent',
        ].join(' ')}
      >
        {replayMode && phase !== 'inactive' ? 'Replay on' : 'Replay'}
      </button>
    </div>
  )
}
