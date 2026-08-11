import type { ReplayConnectionStatus, ReplayPhase } from '@/types/replay'

interface ReplayStatusPillProps {
  phase: ReplayPhase
  connection: ReplayConnectionStatus
}

export function ReplayStatusPill({ phase, connection }: ReplayStatusPillProps) {
  let label: string | null = null
  if (phase === 'buffer_loading') {
    label = 'Buffer loading…'
  } else if (phase === 'completed') {
    label = 'Completed'
  } else if (phase === 'seeking') {
    label = 'Seeking…'
  } else if (phase === 'connecting') {
    label = 'Connecting…'
  }

  const showDot =
    connection === 'open' ||
    connection === 'amber' ||
    connection === 'red' ||
    connection === 'connecting'

  const dotClass =
    connection === 'open'
      ? 'bg-bull'
      : connection === 'amber'
        ? 'bg-amber-400'
        : connection === 'red'
          ? 'bg-bear'
          : connection === 'connecting'
            ? 'bg-text-secondary animate-pulse'
            : 'bg-transparent'

  return (
    <div className="flex items-center gap-2 text-xs text-text-secondary">
      {showDot ? (
        <span
          aria-label={`Connection ${connection}`}
          className={`inline-block h-2 w-2 rounded-full ${dotClass}`}
        />
      ) : null}
      {label ? (
        <span
          className={`rounded px-1.5 py-0.5 ${
            phase === 'completed'
              ? 'bg-accent/15 text-accent'
              : 'bg-border/40 text-text-secondary'
          }`}
        >
          {label}
        </span>
      ) : null}
    </div>
  )
}
