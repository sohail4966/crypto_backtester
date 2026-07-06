import { useCallback, useMemo, useRef, useState } from 'react'
import { ReplayConnectionDot, ReplayStatusPill } from '@/components/Replay/ReplayStatusPill'
import { useReplayStore } from '@/stores/replayStore'
import { REPLAY_SPEED_OPTIONS, replayProgress } from '@/types/replay'

interface ReplayBottomBarProps {
  onPlay: () => void
  onPause: () => void
  onStop: () => void
  onStep: () => void
  onSeek: (to: number) => void
  onSetSpeed: (speed: number) => void
}

export function ReplayBottomBar({
  onPlay,
  onPause,
  onStop,
  onStep,
  onSeek,
  onSetSpeed,
}: ReplayBottomBarProps) {
  const phase = useReplayStore((state) => state.phase)
  const speed = useReplayStore((state) => state.speed)
  const cursor = useReplayStore((state) => state.cursor)
  const startAnchor = useReplayStore((state) => state.startAnchor)
  const latestAvailable = useReplayStore((state) => state.latestAvailable)
  const pendingSeekCursor = useReplayStore((state) => state.pendingSeekCursor)

  const isPlaying = phase === 'playing'
  const isCompleted = phase === 'completed'
  const scrubValue = pendingSeekCursor ?? cursor ?? startAnchor ?? 0
  const min = startAnchor ?? 0
  const max = latestAvailable ?? min
  const progress = replayProgress(scrubValue, startAnchor, latestAvailable)

  const [showTooltip, setShowTooltip] = useState(false)
  const seekTimeoutRef = useRef<number | null>(null)

  const speedOptions = useMemo(() => [...REPLAY_SPEED_OPTIONS], [])

  const handleScrub = useCallback(
    (value: number) => {
      useReplayStore.getState().beginSeek(value)
      if (seekTimeoutRef.current != null) {
        window.clearTimeout(seekTimeoutRef.current)
      }
      seekTimeoutRef.current = window.setTimeout(() => {
        onSeek(value)
      }, 150)
    },
    [onSeek],
  )

  return (
    <div className="flex shrink-0 items-center gap-3 border-t border-border bg-surface px-4 py-2">
      <ReplayConnectionDot />

      <button
        type="button"
        aria-label={isPlaying ? 'Pause replay' : 'Play replay'}
        disabled={isCompleted || phase === 'connecting' || phase === 'seeking'}
        onClick={isPlaying ? onPause : onPlay}
        className="rounded border border-border px-2.5 py-1 text-xs text-text transition-colors hover:border-accent/40 disabled:cursor-not-allowed disabled:opacity-40"
      >
        {isPlaying ? 'Pause' : 'Play'}
      </button>

      <button
        type="button"
        aria-label="Stop replay"
        onClick={onStop}
        className="rounded border border-border px-2.5 py-1 text-xs text-text transition-colors hover:border-bear/40 hover:text-bear"
      >
        Stop
      </button>

      <button
        type="button"
        aria-label="Step forward one bar"
        disabled={isCompleted || phase === 'connecting'}
        onClick={onStep}
        className="rounded border border-border px-2.5 py-1 text-xs text-text transition-colors hover:border-accent/40 disabled:cursor-not-allowed disabled:opacity-40"
      >
        Step
      </button>

      <label className="flex items-center gap-1 text-xs text-text-secondary">
        <span className="sr-only">Playback speed</span>
        <select
          value={speed}
          onChange={(event) => onSetSpeed(Number(event.target.value))}
          className="rounded border border-border bg-bg px-2 py-1 text-xs text-text"
        >
          {speedOptions.map((option) => (
            <option key={option} value={option}>
              {option}×
            </option>
          ))}
        </select>
      </label>

      <div
        className="relative min-w-0 flex-1"
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
      >
        <input
          type="range"
          min={min}
          max={Math.max(min, max)}
          step={1}
          value={scrubValue}
          disabled={startAnchor == null || latestAvailable == null || phase === 'connecting'}
          onChange={(event) => handleScrub(Number(event.target.value))}
          className="w-full accent-accent"
          aria-label="Replay scrubber"
          style={{
            background: `linear-gradient(to right, var(--color-accent) ${progress * 100}%, var(--color-border) ${progress * 100}%)`,
          }}
        />
        {showTooltip ? (
          <div className="pointer-events-none absolute -top-8 left-1/2 -translate-x-1/2 whitespace-nowrap rounded bg-surface px-2 py-1 text-[10px] text-text-secondary shadow">
            Progress vs latest available data ({Math.round(progress * 100)}%)
          </div>
        ) : null}
      </div>

      <ReplayStatusPill />
    </div>
  )
}
