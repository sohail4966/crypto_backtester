import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  clearAuthToken,
  resetAuthTokenForTests,
  setAuthToken,
} from '@/services/authToken'

vi.mock('@/services/api', async () => {
  const actual = await vi.importActual<typeof import('@/services/api')>('@/services/api')
  return {
    ...actual,
    apiRequest: vi.fn(),
  }
})

import { apiRequest } from '@/services/api'
import {
  getWsConnectUrl,
  getWsTicket,
  isWsTicketAuthEnabled,
} from '@/services/wsTicketClient'

const mockedApi = vi.mocked(apiRequest)

describe('wsTicketClient', () => {
  beforeEach(() => {
    resetAuthTokenForTests()
    clearAuthToken()
    mockedApi.mockReset()
    vi.unstubAllEnvs()
  })

  it('isWsTicketAuthEnabled defaults OFF in dev and ON in prod', () => {
    vi.stubEnv('DEV', true)
    vi.stubEnv('VITE_WS_TICKET', undefined as unknown as string)
    expect(isWsTicketAuthEnabled()).toBe(false)

    vi.stubEnv('DEV', false)
    vi.stubEnv('VITE_WS_TICKET', undefined as unknown as string)
    expect(isWsTicketAuthEnabled()).toBe(true)
  })

  it('isWsTicketAuthEnabled honours explicit true/false overrides', () => {
    vi.stubEnv('DEV', true)
    vi.stubEnv('VITE_WS_TICKET', 'true')
    expect(isWsTicketAuthEnabled()).toBe(true)

    vi.stubEnv('DEV', false)
    vi.stubEnv('VITE_WS_TICKET', 'false')
    expect(isWsTicketAuthEnabled()).toBe(false)
  })

  it('getWsTicket returns null when no JWT is present', async () => {
    vi.stubEnv('VITE_WS_TICKET', 'true')
    expect(await getWsTicket()).toBeNull()
    expect(mockedApi).not.toHaveBeenCalled()
  })

  it('getWsTicket POSTs to /ws/tickets and returns the opaque value', async () => {
    setAuthToken('jwt-abc')
    mockedApi.mockResolvedValueOnce({ ticket: 'opaque-hex', expires_in: 60 })
    const ticket = await getWsTicket()
    expect(ticket).toBe('opaque-hex')
    expect(mockedApi).toHaveBeenCalledWith('/ws/tickets', { method: 'POST' })
  })

  it('getWsConnectUrl uses ?ticket= when the flag is on', async () => {
    vi.stubEnv('VITE_WS_TICKET', 'true')
    setAuthToken('jwt-abc')
    mockedApi.mockResolvedValueOnce({ ticket: 'hex-123', expires_in: 30 })
    const url = await getWsConnectUrl('wss://example/ws/live')
    expect(url).toBe('wss://example/ws/live?ticket=hex-123')
  })

  it('getWsConnectUrl falls back to legacy ?token= when the flag is off', async () => {
    vi.stubEnv('VITE_WS_TICKET', 'false')
    setAuthToken('legacy-jwt')
    const url = await getWsConnectUrl('wss://example/ws/live')
    expect(url).toBe('wss://example/ws/live?token=legacy-jwt')
    expect(mockedApi).not.toHaveBeenCalled()
  })

  it('getWsConnectUrl returns the base URL when there is no auth at all', async () => {
    vi.stubEnv('VITE_WS_TICKET', 'true')
    const url = await getWsConnectUrl('wss://example/ws/live')
    expect(url).toBe('wss://example/ws/live')
  })
})
