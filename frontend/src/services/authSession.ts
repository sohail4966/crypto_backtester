import { USER_ID_STORAGE_KEY } from '@/constants/watchlist'
import { clearAuthToken } from '@/services/authToken'
import { useAuthStore } from '@/stores/authStore'

/** Latch so parallel 401 responses clear storage / notify once. */
let clearing = false

export function resetAuthFailureLatch(): void {
  clearing = false
}

/**
 * Clears local auth state once after an authenticated request gets 401/403.
 * Callers (WatchlistRoot / AuthGate) react via authStore.session === 'expired'.
 */
export function notifyAuthFailure(code: string | null = null): void {
  if (clearing) {
    return
  }
  clearing = true
  try {
    clearAuthToken()
    try {
      globalThis.localStorage?.removeItem(USER_ID_STORAGE_KEY)
    } catch {
      // ignore storage failures
    }
    useAuthStore.getState().markExpired(code)
  } finally {
    // Allow a later successful login to be followed by a future expiry clear.
    queueMicrotask(() => {
      clearing = false
    })
  }
}
