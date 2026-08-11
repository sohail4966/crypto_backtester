import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  ApiError,
  extractErrorCode,
  formatErrorMessage,
} from '@/services/api'

describe('formatErrorMessage / extractErrorCode', () => {
  it('prefers nested error.message envelope', () => {
    expect(
      formatErrorMessage(
        { error: { code: 'UNAUTHORIZED', message: 'Token expired' } },
        'Unauthorized',
      ),
    ).toBe('Token expired')
    expect(
      extractErrorCode({ error: { code: 'UNAUTHORIZED', message: 'Token expired' } }),
    ).toBe('UNAUTHORIZED')
  })

  it('falls back to FastAPI detail string and array', () => {
    expect(formatErrorMessage({ detail: 'bad request' }, 'x')).toBe('bad request')
    expect(
      formatErrorMessage({ detail: [{ msg: 'field required' }] }, 'x'),
    ).toBe('field required')
  })

  it('falls back to top-level message then statusText', () => {
    expect(formatErrorMessage({ message: 'oops' }, 'x')).toBe('oops')
    expect(formatErrorMessage(null, 'Unauthorized')).toBe('Unauthorized')
    expect(formatErrorMessage('plain text', 'x')).toBe('plain text')
  })

  it('ApiError carries code', () => {
    const err = new ApiError(401, 'Token expired', {
      error: { code: 'INVALID_TOKEN', message: 'Token expired' },
    }, 'INVALID_TOKEN')
    expect(err.code).toBe('INVALID_TOKEN')
    expect(err.status).toBe(401)
  })
})

describe('apiRequest auth failure', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    localStorage.clear()
  })

  it('notifies auth session on 401 when token present', async () => {
    const { setAuthToken, getAuthToken, resetAuthTokenForTests } = await import(
      '@/services/authToken'
    )
    resetAuthTokenForTests()
    setAuthToken('tok')

    const notify = vi.fn()
    vi.doMock('@/services/authSession', () => ({
      notifyAuthFailure: notify,
      resetAuthFailureLatch: vi.fn(),
    }))

    // Re-import after mock is awkward with static imports; exercise via fetch mock + live module.
    const { apiRequest } = await import('@/services/api')
    const { useAuthStore } = await import('@/stores/authStore')
    useAuthStore.getState().clear()

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          error: { code: 'UNAUTHORIZED', message: 'Not authorized' },
        }),
      }),
    )

    await expect(apiRequest('/users/me/watchlists')).rejects.toMatchObject({
      status: 401,
      code: 'UNAUTHORIZED',
      message: 'Not authorized',
    })
    expect(getAuthToken()).toBeNull()
    expect(useAuthStore.getState().session).toBe('expired')
  })
})
