import { useCallback, useRef, useState } from 'react'
import { PANE_RESIZE_HANDLE_HEIGHT } from '@/constants/chart'

interface PaneResizeHandleProps {
  onDrag: (deltaY: number) => void
}

export function PaneResizeHandle({ onDrag }: PaneResizeHandleProps) {
  const draggingRef = useRef(false)
  const lastYRef = useRef(0)
  const [dragging, setDragging] = useState(false)

  const onPointerDown = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      event.preventDefault()
      event.stopPropagation()
      draggingRef.current = true
      setDragging(true)
      lastYRef.current = event.clientY
      event.currentTarget.setPointerCapture(event.pointerId)
    },
    [],
  )

  const onPointerMove = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      if (!draggingRef.current) {
        return
      }
      const deltaY = event.clientY - lastYRef.current
      if (deltaY === 0) {
        return
      }
      lastYRef.current = event.clientY
      onDrag(deltaY)
    },
    [onDrag],
  )

  const endDrag = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    draggingRef.current = false
    setDragging(false)
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId)
    }
  }, [])

  return (
    <div
      role="separator"
      aria-orientation="horizontal"
      aria-label="Resize pane"
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={endDrag}
      onPointerCancel={endDrag}
      className={`group relative z-20 shrink-0 touch-none select-none ${
        dragging ? 'bg-accent/50' : 'bg-border/30 hover:bg-accent/35'
      }`}
      style={{ height: PANE_RESIZE_HANDLE_HEIGHT }}
    >
      <div
        className="absolute inset-x-0 -top-2 -bottom-2 cursor-row-resize"
        aria-hidden
      />
      <div
        className={`pointer-events-none absolute inset-x-0 top-1/2 mx-auto -translate-y-1/2 rounded-full transition-all ${
          dragging
            ? 'h-1 w-16 bg-accent'
            : 'h-0.5 w-12 bg-border group-hover:h-1 group-hover:w-16 group-hover:bg-accent/80'
        }`}
      />
    </div>
  )
}
