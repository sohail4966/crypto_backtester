import { useEffect } from 'react'
import { LAYOUT_PRESET_BY_ALT_DIGIT } from '@/constants/workspace'
import { useWorkspaceStore } from '@/stores/workspaceStore'

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) {
    return false
  }
  const tag = target.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') {
    return true
  }
  return target.isContentEditable
}

interface UseWorkspaceKeyboardArgs {
  onSave: () => void
}

export function useWorkspaceKeyboard({ onSave }: UseWorkspaceKeyboardArgs): void {
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (isEditableTarget(event.target)) {
        return
      }

      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
        event.preventDefault()
        onSave()
        return
      }

      if (event.altKey && !event.ctrlKey && !event.metaKey) {
        const preset = LAYOUT_PRESET_BY_ALT_DIGIT[event.key]
        if (preset) {
          event.preventDefault()
          useWorkspaceStore.getState().setLayoutPreset(preset)
        }
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [onSave])
}
