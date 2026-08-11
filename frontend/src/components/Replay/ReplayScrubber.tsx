import { useMemo, useRef, useState } from 'react'

interface ReplayScrubberProps {
  startAnchor: number | null
  cursor: number | null
  latestAvailable: number | null
  completed: boolean
  disabled?: boolean
  onSeek: (to: number) => void
}

function formatUnix(ts: number): string {
  try {
    return new Date(ts * 1000).toISOString().replace('T', ' ').slice(0, 19)
  } catch {
    return String(ts)
  }
}

export function ReplayScrubber({
  startAnchor,
  cursor,
  latestAvailable,
  completed,
  disabled,
  onSeek,
}: ReplayScrubberProps) {
  const [dragging, setDragging] = useState(false)
  const [draftRatio, setDraftRatio] = useState(0)
  const trackRef = useRef<HTMLDivElement>(null)

  const denom =
    startAnchor != null && latestAvailable != null
      ? latestAvailable - startAnchor
      : 0

  const progress = useMemo(() => {
    if (completed && cursor != null && latestAvailable != null && cursor === latestAvailable) {
      return 1
    }
    if (startAnchor == null || cursor == null || latestAvailable == null || denom <= 0) {
      return 0
    }
    return Math.min(1, Math.max(0, (cursor - startAnchor) / denom))
  }, [completed, cursor, denom, latestAvailable, startAnchor])

  const inactive = disabled || startAnchor == null || latestAvailable == null || denom <= 0
  const displayRatio = dragging ? draftRatio : progress

  const ratioFromClientX = (clientX: number): number => {
    const el = trackRef.current
    if (!el) {
      return 0
    }
    const rect = el.getBoundingClientRect()
    if (rect.width <= 0) {
      return 0
    }
    return Math.min(1, Math.max(0, (clientX - rect.left) / rect.width))
  }

  const commitSeek = (ratio: number) => {
    if (inactive || startAnchor == null || latestAvailable == null) {
      return
    }
    const to = Math.round(startAnchor + ratio * denom)
    onSeek(to)
  }

  const tooltip =
    cursor != null
      ? `Progress = (cursor − start) / (latestAvailable − start). Latest updates as new candles arrive. Cursor ${formatUnix(cursor)}${
          latestAvailable != null ? ` / latest ${formatUnix(latestAvailable)}` : ''
        }`
      : 'Progress = (cursor − start) / (latestAvailable − start). Latest updates as new candles arrive.'

  return (
    <div className="flex min-w-0 flex-1 flex-col gap-0.5">
      <div
        ref={trackRef}
        role="slider"
        aria-label="Replay position"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(displayRatio * 100)}
        aria-disabled={inactive}
        title={tooltip}
        tabIndex={inactive ? -1 : 0}
        className={`relative h-2 w-full rounded bg-border/60 ${
          inactive ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'
        }`}
        onPointerDown={(event) => {
          if (inactive) {
            return
          }
          event.currentTarget.setPointerCapture(event.pointerId)
          setDragging(true)
          setDraftRatio(ratioFromClientX(event.clientX))
        }}
        onPointerMove={(event) => {
          if (!dragging || inactive) {
            return
          }
          setDraftRatio(ratioFromClientX(event.clientX))
        }}
        onPointerUp={(event) => {
          if (!dragging || inactive) {
            return
          }
          const ratio = ratioFromClientX(event.clientX)
          setDragging(false)
          setDraftRatio(ratio)
          commitSeek(ratio)
        }}
      >
        <div
          className="absolute inset-y-0 left-0 rounded bg-accent"
          style={{ width: `${displayRatio * 100}%` }}
        />
      </div>
    </div>
  )
}
