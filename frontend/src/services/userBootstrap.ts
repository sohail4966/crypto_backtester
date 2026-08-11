import {
  DEV_USER_PASSWORD,
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

function getErrorCode(error: unknown): string | null {
  if (!(error instanceof ApiError)) {
    return null
  }
  const body = error.body
  if (!body || typeof body !== 'object') {
    return null
  }
  const envelope = body as { error?: { code?: unknown } }
  return typeof envelope.error?.code === 'string' ? envelope.error.code : null
}

export function createUser(
  name = DEV_USER_NAME,
  email = DEV_USER_EMAIL,
): Promise<UserResponse> {
  return apiRequest<UserResponse>('/users', {
    method: 'POST',
    body: JSON.stringify({ name, email }),
  })
}

export function getUser(userId: string): Promise<UserResponse> {
  return apiRequest<UserResponse>(`/users/${encodeURIComponent(userId)}`)
}

export function registerUser(
  name = DEV_USER_NAME,
  email = DEV_USER_EMAIL,
  password = DEV_USER_PASSWORD,
): Promise<AuthTokenResponse> {
  return apiRequest<AuthTokenResponse>('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ name, email, password }),
  })
}

export function loginUser(
  email = DEV_USER_EMAIL,
  password = DEV_USER_PASSWORD,
): Promise<AuthTokenResponse> {
  return apiRequest<AuthTokenResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

export function claimUser(
  email = DEV_USER_EMAIL,
  password = DEV_USER_PASSWORD,
): Promise<AuthTokenResponse> {
  return apiRequest<AuthTokenResponse>('/auth/claim', {
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
  return auth.user_id
}

async function obtainDevToken(): Promise<string> {
  try {
    return storeAuthSession(await registerUser())
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 422) {
      throw error
    }
    const code = getErrorCode(error)
    if (code !== 'EMAIL_EXISTS') {
      throw error
    }
    try {
      return storeAuthSession(await claimUser())
    } catch (claimError) {
      if (
        claimError instanceof ApiError &&
        getErrorCode(claimError) === 'PASSWORD_ALREADY_SET'
      ) {
        return storeAuthSession(await loginUser())
      }
      // Legacy passwordless user path: create may have raced; try claim after createUser recover
      try {
        const created = await createUser()
        storeUserId(created.id)
        return storeAuthSession(await claimUser())
      } catch {
        throw claimError
      }
    }
  }
}

async function ensureUserIdOnce(): Promise<string> {
  const stored = readStoredUserId()
  const token = getAuthToken()

  if (stored && token) {
    try {
      const user = await getUser(stored)
      storeUserId(user.id)
      return user.id
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        await clearStaleUser(stored)
        return obtainDevToken()
      }
      throw error
    }
  }

  if (stored && !token) {
    try {
      await getUser(stored)
      try {
        return storeAuthSession(await claimUser())
      } catch (claimError) {
        if (
          claimError instanceof ApiError &&
          getErrorCode(claimError) === 'PASSWORD_ALREADY_SET'
        ) {
          return storeAuthSession(await loginUser())
        }
        throw claimError
      }
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        await clearStaleUser(stored)
        return obtainDevToken()
      }
      throw error
    }
  }

  return obtainDevToken()
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
  clearAuthToken()
}

export { getErrorCode, clearStaleUser }
