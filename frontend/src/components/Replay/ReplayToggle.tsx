import { useChartStore } from '@/stores/chartStore'
import { useReplayStore } from '@/stores/replayStore'

interface ReplayToggleProps {
  onToggleOff: () => void
}

export function ReplayToggle({ onToggleOff }: ReplayToggleProps) {
  const replayMode = useChartStore((s) => s.replayMode)
  const setReplayMode = useChartStore((s) => s.setReplayMode)

  const handleClick = () => {
    if (replayMode) {
      onToggleOff()
      return
    }
    setReplayMode(true)
    useReplayStore.getState().enterPickAnchor()
  }

  return (
    <button
      type="button"
      aria-pressed={replayMode}
      onClick={handleClick}
      className={`rounded border px-2.5 py-1 text-xs transition-colors ${
        replayMode
          ? 'border-accent bg-accent/10 text-accent'
          : 'border-border text-text hover:border-accent/40 hover:text-accent'
      }`}
    >
      Replay
    </button>
  )
}
