import {
  DEV_USER_PASSWORD,
  allowDevAuth,
} from '@/constants/auth'
import {
  DEV_USER_EMAIL,
  DEV_USER_NAME,
  USER_ID_STORAGE_KEY,
} from '@/constants/watchlist'
import { ApiError, apiRequest } from '@/services/api'
import {
  clearAuthToken,
  getAuthToken,
  setAuthToken,
} from '@/services/authToken'
import { deleteWatchlistCache } from '@/services/watchlistCache'
import { useAuthStore } from '@/stores/authStore'
import type { UserResponse } from '@/types/watchlist'

export type AuthTokenResponse = {
  access_token: string
  token_type: string
  user_id: string
  email: string
  name: string
  created_at: string
  updated_at: string
}

export class AuthRequiredError extends Error {
  constructor(message = 'Authentication required') {
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

/** Authenticated session probe (BE-016 / FE-002). */
export function getCurrentUser(): Promise<UserResponse> {
  return apiRequest<UserResponse>('/auth/me')
}

export function registerUser(
  name: string,
  email: string,
  password: string,
): Promise<AuthTokenResponse> {
  return apiRequest<AuthTokenResponse>('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ name, email, password }),
  })
}

export function loginUser(
  email: string,
  password: string,
): Promise<AuthTokenResponse> {
  return apiRequest<AuthTokenResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
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
  clearAuthToken()
  await deleteWatchlistCache(userId)
}

function storeAuthSession(auth: AuthTokenResponse): string {
  setAuthToken(auth.access_token)
  storeUserId(auth.user_id)
  useAuthStore.getState().setAuthenticated({
    userId: auth.user_id,
    email: auth.email,
    name: auth.name,
  })
  return auth.user_id
}

/**
 * Silent local-dev token path. Gated by allowDevAuth(); not used in production builds
 * unless VITE_ALLOW_DEV_AUTH is explicitly enabled.
 */
async function obtainDevToken(): Promise<string> {
  try {
    return storeAuthSession(
      await registerUser(DEV_USER_NAME, DEV_USER_EMAIL, DEV_USER_PASSWORD),
    )
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 422) {
      throw error
    }
    const code = getErrorCode(error)
    // BE-024/G-008: register conflicts use REGISTRATION_FAILED (legacy EMAIL_EXISTS kept for older APIs).
    if (
      code === 'REGISTRATION_FAILED' ||
      code === 'EMAIL_EXISTS' ||
      code === 'AUTH_FAILED'
    ) {
      return storeAuthSession(await loginUser(DEV_USER_EMAIL, DEV_USER_PASSWORD))
    }
    throw error
  }
}

async function ensureUserIdOnce(): Promise<string> {
  const stored = readStoredUserId()
  const token = getAuthToken()

  if (stored && token) {
    try {
      const user = await getCurrentUser()
      storeUserId(user.id)
      useAuthStore.getState().setAuthenticated({
        userId: user.id,
        email: user.email,
        name: user.name,
      })
      return user.id
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.status === 401 || error.status === 403) {
          await clearStaleUser(stored)
          useAuthStore.getState().setNeedsAuth()
          if (allowDevAuth()) {
            return obtainDevToken()
          }
          throw new AuthRequiredError('Session expired')
        }
        if (error.status === 404) {
          await clearStaleUser(stored)
          if (allowDevAuth()) {
            return obtainDevToken()
          }
          useAuthStore.getState().setNeedsAuth()
          throw new AuthRequiredError('Stored user is invalid')
        }
      }
      throw error
    }
  }

  if (stored && !token) {
    // Missing JWT — reclaim via auth UX / DEV login without wiping watchlist cache yet.
    if (allowDevAuth()) {
      return obtainDevToken()
    }
    clearStoredUserId()
    useAuthStore.getState().setNeedsAuth()
    throw new AuthRequiredError()
  }

  if (allowDevAuth()) {
    return obtainDevToken()
  }

  useAuthStore.getState().setNeedsAuth()
  throw new AuthRequiredError()
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

/**
 * Explicit login/register for the Auth UI. Stores session and returns user id.
 */
export async function authenticateWithCredentials(input: {
  mode: 'login' | 'register'
  email: string
  password: string
  name?: string
}): Promise<string> {
  const email = input.email.trim().toLowerCase()
  const password = input.password
  if (!email || !password) {
    throw new AuthRequiredError('Email and password are required')
  }

  if (input.mode === 'register') {
    const name = (input.name ?? email.split('@')[0] ?? 'User').trim() || 'User'
    return storeAuthSession(await registerUser(name, email, password))
  }
  return storeAuthSession(await loginUser(email, password))
}

/** Test helper — resets the in-flight bootstrap latch. */
export function resetUserBootstrapLatch(): void {
  inFlight = null
}

export function clearLocalUserId(): void {
  clearStoredUserId()
  clearAuthToken()
  useAuthStore.getState().clear()
}

export { clearStaleUser }
