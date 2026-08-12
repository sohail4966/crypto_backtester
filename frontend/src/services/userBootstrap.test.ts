import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '@/services/api'
import {
  DEV_USER_EMAIL,
  DEV_USER_NAME,
  USER_ID_STORAGE_KEY,
} from '@/constants/watchlist'
import { deleteWatchlistCache } from '@/services/watchlistCache'
import { useAuthStore } from '@/stores/authStore'

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
import { ensureUserId, resetUserBootstrapLatch } from '@/services/userBootstrap'

const mockedApi = vi.mocked(apiRequest)
const mockedDeleteCache = vi.mocked(deleteWatchlistCache)

function userResponse(userId: string) {
  return {
    id: userId,
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
    useAuthStore.getState().clear()
  })

  it('reuses a stored user via GET /users/{id}', async () => {
    localStorage.setItem(USER_ID_STORAGE_KEY, 'user-1')
    mockedApi.mockResolvedValueOnce(userResponse('user-1'))

    await expect(ensureUserId()).resolves.toBe('user-1')
    expect(mockedApi).toHaveBeenCalledWith('/users/user-1')
    expect(useAuthStore.getState().userId).toBe('user-1')
  })

  it('creates a passwordless user when none is stored', async () => {
    mockedApi.mockResolvedValueOnce(userResponse('new-user'))

    await expect(ensureUserId()).resolves.toBe('new-user')
    expect(mockedApi).toHaveBeenCalledWith(
      '/users',
      expect.objectContaining({
        method: 'POST',
      }),
    )
    const body = JSON.parse(String(mockedApi.mock.calls[0]?.[1]?.body)) as {
      name: string
      email: string
    }
    expect(body.name).toBe(DEV_USER_NAME)
    expect(body.email).toContain('@')
    expect(localStorage.getItem(USER_ID_STORAGE_KEY)).toBe('new-user')
  })

  it('clears a stale 404 ID/cache and creates a new user', async () => {
    localStorage.setItem(USER_ID_STORAGE_KEY, 'stale')
    mockedApi
      .mockRejectedValueOnce(
        new ApiError(404, 'missing', { error: { code: 'USER_NOT_FOUND', message: 'gone' } }, 'USER_NOT_FOUND'),
      )
      .mockResolvedValueOnce(userResponse('fresh'))

    await expect(ensureUserId()).resolves.toBe('fresh')
    expect(mockedDeleteCache).toHaveBeenCalledWith('stale')
    expect(localStorage.getItem(USER_ID_STORAGE_KEY)).toBe('fresh')
  })

  it('deduplicates concurrent calls under Strict Mode', async () => {
    let resolveCreate: ((value: unknown) => void) | undefined
    mockedApi.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveCreate = resolve
        }),
    )

    const first = ensureUserId()
    const second = ensureUserId()
    expect(mockedApi).toHaveBeenCalledTimes(1)

    resolveCreate?.(userResponse('shared'))

    await expect(first).resolves.toBe('shared')
    await expect(second).resolves.toBe('shared')
  })

  it('does not loop and propagates unrelated errors', async () => {
    mockedApi.mockRejectedValueOnce(
      new ApiError(500, 'boom', { error: { code: 'X', message: 'boom' } }, 'X'),
    )
    await expect(ensureUserId()).rejects.toBeInstanceOf(ApiError)
    expect(mockedApi).toHaveBeenCalledTimes(1)
  })
})
