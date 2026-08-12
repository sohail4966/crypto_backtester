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
        { error: { code: 'NOT_FOUND', message: 'missing' } },
        'Not Found',
      ),
    ).toBe('missing')
    expect(
      extractErrorCode({ error: { code: 'NOT_FOUND', message: 'missing' } }),
    ).toBe('NOT_FOUND')
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
    const err = new ApiError(404, 'missing', {
      error: { code: 'USER_NOT_FOUND', message: 'missing' },
    }, 'USER_NOT_FOUND')
    expect(err.code).toBe('USER_NOT_FOUND')
    expect(err.status).toBe(404)
  })
})
