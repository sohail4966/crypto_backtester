import { useEffect } from 'react'
import { SHORTCUT_TO_TOOL } from '@/constants/drawings'
import { useDrawingStore } from '@/stores/drawingStore'

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

export function useDrawingKeyboard(enabled = true): void {
  useEffect(() => {
    if (!enabled) {
      return
    }

    const onKeyDown = (event: KeyboardEvent) => {
      if (isEditableTarget(event.target)) {
        return
      }
      if (event.metaKey || event.ctrlKey || event.altKey) {
        return
      }

      const store = useDrawingStore.getState()

      if (event.key === 'Escape') {
        if (store.handleEscape()) {
          event.preventDefault()
        }
        return
      }

      if (event.key === 'Delete' || event.key === 'Backspace') {
        if (store.selectedId) {
          event.preventDefault()
          store.removeSelected()
        }
        return
      }

      const tool = SHORTCUT_TO_TOOL[event.key.toLowerCase()]
      if (tool) {
        event.preventDefault()
        store.setActiveTool(tool)
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [enabled])
}
