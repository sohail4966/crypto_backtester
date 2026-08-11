import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { AUTH_TOKEN_STORAGE_KEY } from '@/constants/auth'
import {
  clearAuthToken,
  getAuthToken,
  resetAuthTokenForTests,
  setAuthToken,
} from '@/services/authToken'

describe('authToken (in-memory)', () => {
  beforeEach(() => {
    resetAuthTokenForTests()
    localStorage.clear()
  })

  afterEach(() => {
    resetAuthTokenForTests()
    localStorage.clear()
  })

  it('starts null and returns the in-memory value after set', () => {
    expect(getAuthToken()).toBeNull()
    setAuthToken('tok-1')
    expect(getAuthToken()).toBe('tok-1')
  })

  it('never writes the JWT to localStorage', () => {
    setAuthToken('tok-2')
    expect(localStorage.getItem(AUTH_TOKEN_STORAGE_KEY)).toBeNull()
  })

  it('clearAuthToken drops the in-memory value', () => {
    setAuthToken('tok-3')
    clearAuthToken()
    expect(getAuthToken()).toBeNull()
  })

  it('setAuthToken removes any legacy localStorage residue', () => {
    localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, 'legacy')
    setAuthToken('fresh')
    expect(localStorage.getItem(AUTH_TOKEN_STORAGE_KEY)).toBeNull()
    expect(getAuthToken()).toBe('fresh')
  })
})
