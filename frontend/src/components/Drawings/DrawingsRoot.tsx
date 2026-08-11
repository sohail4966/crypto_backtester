import { useEffect, type ReactNode } from 'react'
import { DRAWING_PERSIST_DEBOUNCE_MS } from '@/constants/drawings'
import { readDrawingsCache, writeDrawingsCache } from '@/services/drawingCache'
import { useDrawingStore } from '@/stores/drawingStore'

interface DrawingsRootProps {
  children: ReactNode
}

export function DrawingsRoot({ children }: DrawingsRootProps) {
  const drawings = useDrawingStore((s) => s.drawings)
  const hydrated = useDrawingStore((s) => s.hydrated)

  useEffect(() => {
    let cancelled = false

    void (async () => {
      try {
        const cache = await readDrawingsCache()
        if (cancelled) {
          return
        }
        // Re-hydrate on remount (React Strict Mode) so we never stay stuck
        // with hydrated=false after a cancelled first pass.
        useDrawingStore.getState().hydrate(cache?.drawings ?? [])
      } catch {
        if (!cancelled) {
          useDrawingStore.getState().hydrate([])
        }
      }
    })()

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!hydrated) {
      return
    }
    const timer = window.setTimeout(() => {
      void writeDrawingsCache(drawings).catch(() => {
        /* persistence errors are non-fatal */
      })
    }, DRAWING_PERSIST_DEBOUNCE_MS)
    return () => window.clearTimeout(timer)
  }, [drawings, hydrated])

  return children
}
