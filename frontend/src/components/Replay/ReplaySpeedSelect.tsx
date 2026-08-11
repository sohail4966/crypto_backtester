import type { ReplaySpeed } from '@/types/replay'
import { REPLAY_SPEEDS } from '@/constants/replay'

interface ReplaySpeedSelectProps {
  value: ReplaySpeed
  onChange: (speed: ReplaySpeed) => void
  disabled?: boolean
}

export function ReplaySpeedSelect({
  value,
  onChange,
  disabled,
}: ReplaySpeedSelectProps) {
  return (
    <label className="flex items-center gap-1.5 text-xs text-text-secondary">
      <span className="sr-only">Replay speed</span>
      <select
        aria-label="Replay speed"
        value={value}
        disabled={disabled}
        onChange={(event) => {
          const next = Number(event.target.value) as ReplaySpeed
          onChange(next)
        }}
        className="rounded border border-border bg-bg px-1.5 py-1 text-xs text-text"
      >
        {REPLAY_SPEEDS.map((speed) => (
          <option key={speed} value={speed}>
            {speed}×
          </option>
        ))}
      </select>
    </label>
  )
}
