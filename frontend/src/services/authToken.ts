import { AUTH_TOKEN_STORAGE_KEY } from '@/constants/auth'

export function getAuthToken(): string | null {
  try {
    return globalThis.localStorage?.getItem(AUTH_TOKEN_STORAGE_KEY) ?? null
  } catch {
    return null
  }
}

export function setAuthToken(token: string): void {
  globalThis.localStorage?.setItem(AUTH_TOKEN_STORAGE_KEY, token)
}

export function clearAuthToken(): void {
  globalThis.localStorage?.removeItem(AUTH_TOKEN_STORAGE_KEY)
}
