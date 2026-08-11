import { describe, expect, it } from 'vitest'
import {
  WS_CLOSE_NOT_FOUND,
  WS_CLOSE_RATE_LIMITED,
  WS_CLOSE_SUPERSEDED,
  WS_CLOSE_UNAUTHORIZED,
  classifyWsCloseKind,
} from '@/services/wsCloseCode'

describe('classifyWsCloseKind', () => {
  it('maps known BE close codes to distinct kinds', () => {
    expect(classifyWsCloseKind(WS_CLOSE_UNAUTHORIZED)).toBe('unauthorized')
    expect(classifyWsCloseKind(WS_CLOSE_SUPERSEDED)).toBe('superseded')
    expect(classifyWsCloseKind(WS_CLOSE_NOT_FOUND)).toBe('not_found')
    expect(classifyWsCloseKind(WS_CLOSE_RATE_LIMITED)).toBe('rate_limited')
  })

  it('treats 1000 and 1001 as normal closed', () => {
    expect(classifyWsCloseKind(1000)).toBe('closed')
    expect(classifyWsCloseKind(1001)).toBe('closed')
  })

  it('falls back to error for anything else', () => {
    expect(classifyWsCloseKind(1006)).toBe('error')
    expect(classifyWsCloseKind(4500)).toBe('error')
  })

  it('exposes the BE constants at their documented numeric values', () => {
    expect(WS_CLOSE_UNAUTHORIZED).toBe(4401)
    expect(WS_CLOSE_SUPERSEDED).toBe(4402)
    expect(WS_CLOSE_NOT_FOUND).toBe(4404)
    expect(WS_CLOSE_RATE_LIMITED).toBe(4429)
  })
})
