import type { SyncEvent } from '@/types/workspace'

type SyncListener = (event: SyncEvent) => void

const listeners = new Set<SyncListener>()

export function publishSync(event: SyncEvent): void {
  for (const listener of listeners) {
    listener(event)
  }
}

export function subscribeSync(listener: SyncListener): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

/** Test helper — clear subscribers between tests. */
export function resetSyncListeners(): void {
  listeners.clear()
}
