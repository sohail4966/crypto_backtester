import { ReplayScrubber } from '@/components/Replay/ReplayScrubber'
import { ReplaySpeedSelect } from '@/components/Replay/ReplaySpeedSelect'
import { ReplayStatusPill } from '@/components/Replay/ReplayStatusPill'
import type { ReplaySpeed } from '@/types/replay'
import { useReplayStore } from '@/stores/replayStore'

interface ReplayBottomBarProps {
  onPlay: () => void
  onPause: () => void
  onStop: () => void
  onStep: () => void
  onSeek: (to: number) => void
  onSpeedChange: (speed: ReplaySpeed) => void
}

export function ReplayBottomBar({
  onPlay,
  onPause,
  onStop,
  onStep,
  onSeek,
  onSpeedChange,
}: ReplayBottomBarProps) {
  const phase = useReplayStore((s) => s.phase)
  const speed = useReplayStore((s) => s.speed)
  const meta = useReplayStore((s) => s.meta)
  const connection = useReplayStore((s) => s.connection)

  const playing = phase === 'playing'
  const playDisabled = phase === 'completed' || phase === 'connecting'

  return (
    <div
      role="toolbar"
      aria-label="Replay controls"
      className="flex shrink-0 items-center gap-3 border-t border-border bg-surface px-3 py-2"
    >
      <div className="flex items-center gap-1.5">
        {playing ? (
          <button
            type="button"
            aria-label="Pause"
            onClick={onPause}
            className="rounded border border-border px-2 py-1 text-xs text-text hover:border-accent/40"
          >
            Pause
          </button>
        ) : (
          <button
            type="button"
            aria-label="Play"
            disabled={playDisabled}
            onClick={onPlay}
            className="rounded border border-border px-2 py-1 text-xs text-text hover:border-accent/40 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Play
          </button>
        )}
        <button
          type="button"
          aria-label="Step forward"
          onClick={onStep}
          disabled={phase === 'completed' || phase === 'connecting'}
          className="rounded border border-border px-2 py-1 text-xs text-text hover:border-accent/40 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Step
        </button>
        <button
          type="button"
          aria-label="Stop"
          onClick={onStop}
          className="rounded border border-border px-2 py-1 text-xs text-text hover:border-accent/40"
        >
          Stop
        </button>
      </div>

      <ReplaySpeedSelect
        value={speed}
        onChange={onSpeedChange}
        disabled={phase === 'connecting'}
      />

      <ReplayScrubber
        startAnchor={meta?.startAnchor ?? null}
        cursor={meta?.cursor ?? null}
        latestAvailable={meta?.latestAvailable ?? null}
        completed={phase === 'completed'}
        disabled={phase === 'connecting'}
        onSeek={onSeek}
      />

      <ReplayStatusPill phase={phase} connection={connection} />
    </div>
  )
}
