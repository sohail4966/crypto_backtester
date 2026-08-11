import { AUTH_TOKEN_STORAGE_KEY } from '@/constants/auth'

/**
 * In-memory JWT storage (FE-L2-003). Keeps the bearer out of ``localStorage``
 * where XSS or third-party scripts could read it. A future silent-refresh /
 * cookie path can rehydrate this on reload; for now, reloading requires
 * re-signing in.
 *
 * A legacy read of ``localStorage['auth_token']`` is performed exactly once on
 * module init so existing signed-in users are migrated cleanly across the
 * release boundary. The value is then removed from ``localStorage`` so it never
 * lingers on disk again.
 */

let inMemoryToken: string | null = null

function drainLegacyStorage(): void {
  try {
    const legacy = globalThis.localStorage?.getItem(AUTH_TOKEN_STORAGE_KEY)
    if (legacy) {
      inMemoryToken = legacy
    }
  } catch {
    // storage disabled / unavailable
  } finally {
    try {
      globalThis.localStorage?.removeItem(AUTH_TOKEN_STORAGE_KEY)
    } catch {
      // ignore
    }
  }
}

drainLegacyStorage()

export function getAuthToken(): string | null {
  return inMemoryToken
}

export function setAuthToken(token: string): void {
  inMemoryToken = token
  try {
    globalThis.localStorage?.removeItem(AUTH_TOKEN_STORAGE_KEY)
  } catch {
    // ignore
  }
}

export function clearAuthToken(): void {
  inMemoryToken = null
  try {
    globalThis.localStorage?.removeItem(AUTH_TOKEN_STORAGE_KEY)
  } catch {
    // ignore
  }
}

/** Test-only helper — resets the module singleton between test cases. */
export function resetAuthTokenForTests(): void {
  inMemoryToken = null
}
