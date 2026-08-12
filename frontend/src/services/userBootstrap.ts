import {
  DEV_USER_EMAIL,
  DEV_USER_NAME,
  USER_ID_STORAGE_KEY,
} from '@/constants/watchlist'
import { ApiError, apiRequest } from '@/services/api'
import { deleteWatchlistCache } from '@/services/watchlistCache'
import { useAuthStore } from '@/stores/authStore'
import type { UserResponse } from '@/types/watchlist'

export class AuthRequiredError extends Error {
  constructor(message = 'User bootstrap failed') {
    super(message)
    this.name = 'AuthRequiredError'
  }
}

export function getErrorCode(error: unknown): string | null {
  if (error instanceof ApiError) {
    return error.code
  }
  return null
}

export function getUser(userId: string): Promise<UserResponse> {
  return apiRequest<UserResponse>(`/users/${encodeURIComponent(userId)}`)
}

export function createUser(name: string, email: string): Promise<UserResponse> {
  return apiRequest<UserResponse>('/users', {
    method: 'POST',
    body: JSON.stringify({ name, email }),
  })
}

function readStoredUserId(): string | null {
  return localStorage.getItem(USER_ID_STORAGE_KEY)
}

function storeUserId(userId: string): void {
  localStorage.setItem(USER_ID_STORAGE_KEY, userId)
}

function clearStoredUserId(): void {
  localStorage.removeItem(USER_ID_STORAGE_KEY)
}

async function clearStaleUser(userId: string): Promise<void> {
  clearStoredUserId()
  await deleteWatchlistCache(userId)
}

function rememberUser(user: UserResponse): string {
  storeUserId(user.id)
  useAuthStore.getState().setUser({
    userId: user.id,
    email: user.email,
    name: user.name,
  })
  return user.id
}

async function createLocalUser(): Promise<string> {
  const suffix = crypto.randomUUID().slice(0, 8)
  const email = DEV_USER_EMAIL.includes('@')
    ? DEV_USER_EMAIL.replace('@', `+${suffix}@`)
    : `${suffix}@local.dev`
  return rememberUser(await createUser(DEV_USER_NAME, email))
}

async function ensureUserIdOnce(): Promise<string> {
  const stored = readStoredUserId()
  if (stored) {
    try {
      return rememberUser(await getUser(stored))
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        await clearStaleUser(stored)
        return createLocalUser()
      }
      throw error
    }
  }
  return createLocalUser()
}

/** Module-level in-flight promise so Strict Mode cannot double-create users. */
let inFlight: Promise<string> | null = null

export function ensureUserId(): Promise<string> {
  if (inFlight) {
    return inFlight
  }
  inFlight = ensureUserIdOnce().finally(() => {
    inFlight = null
  })
  return inFlight
}

/** Test helper — resets the in-flight bootstrap latch. */
export function resetUserBootstrapLatch(): void {
  inFlight = null
}

export function clearLocalUserId(): void {
  clearStoredUserId()
  useAuthStore.getState().clear()
}

export { clearStaleUser }
