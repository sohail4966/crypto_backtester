import { useEffect } from 'react'
import { useChartStore } from '@/stores/chartStore'
import { useDrawingStore } from '@/stores/drawingStore'
import { sessionActivePhase, useReplayStore } from '@/stores/replayStore'

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) {
    return false
  }
  const tag = target.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') {
    return true
  }
  if (target.isContentEditable) {
    return true
  }
  return Boolean(target.closest('input, textarea, select, [contenteditable="true"]'))
}

interface UseReplayKeyboardOptions {
  play: () => void
  pause: () => void
  step: () => void
}

export function useReplayKeyboard({
  play,
  pause,
  step,
}: UseReplayKeyboardOptions): void {
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (isEditableTarget(event.target)) {
        return
      }

      const phase = useReplayStore.getState().phase

      if (event.key === 'Escape') {
        // Drawings Esc precedence (draft → tool → selection) wins before replay.
        if (useDrawingStore.getState().consumesEscape()) {
          return
        }
        if (phase === 'pick_anchor') {
          event.preventDefault()
          useReplayStore.getState().reset()
          useChartStore.getState().setReplayMode(false)
        }
        return
      }

      if (!sessionActivePhase(phase)) {
        return
      }

      if (event.key === ' ' || event.code === 'Space') {
        event.preventDefault()
        if (phase === 'playing') {
          pause()
        } else if (
          phase === 'paused' ||
          phase === 'ready' ||
          phase === 'buffer_loading'
        ) {
          play()
        }
        return
      }

      if (event.key === 'ArrowRight') {
        event.preventDefault()
        step()
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [play, pause, step])
}
