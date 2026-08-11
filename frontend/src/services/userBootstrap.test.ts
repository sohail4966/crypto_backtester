import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '@/services/api'
import { AUTH_TOKEN_STORAGE_KEY, DEV_USER_PASSWORD } from '@/constants/auth'
import {
  DEV_USER_EMAIL,
  DEV_USER_NAME,
  USER_ID_STORAGE_KEY,
} from '@/constants/watchlist'
import { deleteWatchlistCache } from '@/services/watchlistCache'

vi.mock('@/services/api', async () => {
  const actual = await vi.importActual<typeof import('@/services/api')>('@/services/api')
  return {
    ...actual,
    apiRequest: vi.fn(),
  }
})

vi.mock('@/services/watchlistCache', () => ({
  deleteWatchlistCache: vi.fn(async () => undefined),
}))

import { apiRequest } from '@/services/api'
import {
  ensureUserId,
  resetUserBootstrapLatch,
} from '@/services/userBootstrap'

const mockedApi = vi.mocked(apiRequest)
const mockedDeleteCache = vi.mocked(deleteWatchlistCache)

function authResponse(userId: string) {
  return {
    access_token: 'tok',
    token_type: 'bearer',
    user_id: userId,
    email: DEV_USER_EMAIL,
    name: DEV_USER_NAME,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  }
}

describe('userBootstrap', () => {
  beforeEach(() => {
    localStorage.clear()
    resetUserBootstrapLatch()
    mockedApi.mockReset()
    mockedDeleteCache.mockClear()
  })

  it('reuses stored ID when token is present', async () => {
    localStorage.setItem(USER_ID_STORAGE_KEY, 'user-1')
    localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, 'tok')
    mockedApi.mockResolvedValueOnce({
      id: 'user-1',
      name: 'Dev User',
      email: DEV_USER_EMAIL,
      created_at: '2024-01-01T00:00:00Z',
    })

    await expect(ensureUserId()).resolves.toBe('user-1')
    expect(mockedApi).toHaveBeenCalledWith('/users/user-1')
  })

  it('registers and stores token when absent', async () => {
    mockedApi.mockResolvedValueOnce(authResponse('new-user'))

    await expect(ensureUserId()).resolves.toBe('new-user')
    expect(mockedApi).toHaveBeenCalledWith('/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        name: DEV_USER_NAME,
        email: DEV_USER_EMAIL,
        password: DEV_USER_PASSWORD,
      }),
    })
    expect(localStorage.getItem(USER_ID_STORAGE_KEY)).toBe('new-user')
    expect(localStorage.getItem(AUTH_TOKEN_STORAGE_KEY)).toBe('tok')
  })

  it('claims when register hits EMAIL_EXISTS', async () => {
    mockedApi
      .mockRejectedValueOnce(
        new ApiError(422, 'exists', { error: { code: 'EMAIL_EXISTS', message: 'dup' } }),
      )
      .mockResolvedValueOnce(authResponse('existing'))

    await expect(ensureUserId()).resolves.toBe('existing')
    expect(mockedApi).toHaveBeenNthCalledWith(2, '/auth/claim', {
      method: 'POST',
      body: JSON.stringify({ email: DEV_USER_EMAIL, password: DEV_USER_PASSWORD }),
    })
  })

  it('logs in when claim finds PASSWORD_ALREADY_SET', async () => {
    mockedApi
      .mockRejectedValueOnce(
        new ApiError(422, 'exists', { error: { code: 'EMAIL_EXISTS', message: 'dup' } }),
      )
      .mockRejectedValueOnce(
        new ApiError(422, 'set', {
          error: { code: 'PASSWORD_ALREADY_SET', message: 'set' },
        }),
      )
      .mockResolvedValueOnce(authResponse('existing'))

    await expect(ensureUserId()).resolves.toBe('existing')
    expect(mockedApi).toHaveBeenNthCalledWith(3, '/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email: DEV_USER_EMAIL, password: DEV_USER_PASSWORD }),
    })
  })

  it('deduplicates concurrent calls under Strict Mode', async () => {
    let resolveRegister: ((value: unknown) => void) | undefined
    mockedApi.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveRegister = resolve
        }),
    )

    const first = ensureUserId()
    const second = ensureUserId()
    expect(mockedApi).toHaveBeenCalledTimes(1)

    resolveRegister?.(authResponse('shared'))

    await expect(first).resolves.toBe('shared')
    await expect(second).resolves.toBe('shared')
  })

  it('clears a stale 404 ID/cache and retries once', async () => {
    localStorage.setItem(USER_ID_STORAGE_KEY, 'stale')
    localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, 'tok')
    mockedApi
      .mockRejectedValueOnce(
        new ApiError(404, 'missing', { error: { code: 'USER_NOT_FOUND', message: 'gone' } }),
      )
      .mockResolvedValueOnce(authResponse('fresh'))

    await expect(ensureUserId()).resolves.toBe('fresh')
    expect(mockedDeleteCache).toHaveBeenCalledWith('stale')
    expect(localStorage.getItem(USER_ID_STORAGE_KEY)).toBe('fresh')
  })

  it('does not loop and propagates unrelated errors', async () => {
    mockedApi.mockRejectedValueOnce(new ApiError(500, 'boom', { error: { code: 'X', message: 'boom' } }))
    await expect(ensureUserId()).rejects.toBeInstanceOf(ApiError)
    expect(mockedApi).toHaveBeenCalledTimes(1)
  })
})
