import { replayProgress } from '@/types/replay'
import { useReplayStore } from '@/stores/replayStore'

export function ReplayStatusPill() {
  const phase = useReplayStore((state) => state.phase)
  const bufferLoading = useReplayStore((state) => state.bufferLoading)
  const connectionStatus = useReplayStore((state) => state.connectionStatus)
  const connectionMessage = useReplayStore((state) => state.connectionMessage)

  if (connectionStatus === 'superseded') {
    return (
      <span className="rounded-full bg-amber-500/15 px-2 py-0.5 text-xs text-amber-400">
        Opened elsewhere
      </span>
    )
  }

  if (connectionStatus === 'not_found') {
    return (
      <span className="rounded-full bg-amber-500/15 px-2 py-0.5 text-xs text-amber-400">
        Session not found
      </span>
    )
  }

  if (phase === 'completed') {
    return (
      <span className="rounded-full bg-accent/15 px-2 py-0.5 text-xs text-accent">
        Replay complete
      </span>
    )
  }

  if (bufferLoading || phase === 'buffer_loading') {
    return (
      <span className="rounded-full bg-text-secondary/15 px-2 py-0.5 text-xs text-text-secondary">
        Loading buffer…
      </span>
    )
  }

  if (phase === 'ready') {
    return (
      <span className="rounded-full bg-text-secondary/15 px-2 py-0.5 text-xs text-text-secondary">
        Press Play to begin
      </span>
    )
  }

  if (connectionStatus === 'error' && connectionMessage) {
    return (
      <span className="rounded-full bg-bear/15 px-2 py-0.5 text-xs text-bear">
        {connectionMessage}
      </span>
    )
  }

  return null
}

export function ReplayConnectionDot() {
  const connectionStatus = useReplayStore((state) => state.connectionStatus)
  const phase = useReplayStore((state) => state.phase)

  const color =
    connectionStatus === 'connected'
      ? 'bg-bull'
      : connectionStatus === 'superseded' || connectionStatus === 'not_found'
        ? 'bg-amber-400'
        : phase === 'connecting'
          ? 'bg-amber-400 animate-pulse'
          : connectionStatus === 'error'
            ? 'bg-bear'
            : 'bg-text-secondary'

  return (
    <span
      className={`inline-block h-2 w-2 shrink-0 rounded-full ${color}`}
      title={connectionStatus}
      aria-hidden
    />
  )
}

export function ReplayProgressTooltip({
  cursor,
  startAnchor,
  latestAvailable,
}: {
  cursor: number | null
  startAnchor: number | null
  latestAvailable: number | null
}) {
  const pct = Math.round(replayProgress(cursor, startAnchor, latestAvailable) * 100)
  return (
    <span className="sr-only">
      Progress {pct}% vs latest available data
    </span>
  )
}
