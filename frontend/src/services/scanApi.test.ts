import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/services/api', async () => {
  const actual = await vi.importActual<typeof import('@/services/api')>('@/services/api')
  return {
    ...actual,
    apiRequest: vi.fn(),
  }
})

import { apiRequest } from '@/services/api'
import { getScan, runScan } from '@/services/scanApi'

const mockedApi = vi.mocked(apiRequest)

describe('scanApi', () => {
  beforeEach(() => {
    mockedApi.mockReset()
  })

  it('runScan POSTs the exact ScanCreateRequest body', async () => {
    mockedApi.mockResolvedValueOnce({
      scan_id: 's-1',
      timeframes: ['1h'],
      symbols: ['BTC/USDT'],
      start: 1,
      end: 2,
      alert_trigger: 'edge',
      matches: [],
      alert_count: 0,
      duration_ms: 3,
      scanned_pairs: 1,
      errors: [],
      persisted: true,
    })

    const body = {
      timeframes: ['1h'],
      start: 1,
      end: 2,
      condition: { kind: 'placeholder' },
      symbols: ['BTC/USDT'],
      alert_trigger: 'edge' as const,
      persist: true,
    }
    await runScan(body)
    expect(mockedApi).toHaveBeenCalledWith('/scan', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  })

  it('preserves snake_case response fields verbatim', async () => {
    const payload = {
      scan_id: null,
      timeframes: ['15m', '1h'],
      symbols: [],
      start: 100,
      end: 200,
      alert_trigger: 'level' as const,
      matches: [
        {
          symbol: 'BTC/USDT',
          timeframe: '1h',
          bar_ts: '2026-08-11T00:00:00Z',
          triggered: true,
          close: 60000,
        },
      ],
      alert_count: 1,
      duration_ms: 42,
      scanned_pairs: 2,
      errors: [{ symbol: 'X', timeframe: '1h', error: 'boom' }],
      persisted: false,
    }
    mockedApi.mockResolvedValueOnce(payload)
    const result = await runScan({
      timeframes: ['15m', '1h'],
      start: 100,
      end: 200,
      condition: {},
      persist: false,
    })
    expect(result).toEqual(payload)
    expect(result.scan_id).toBeNull()
    expect(result.matches[0]?.bar_ts).toBe('2026-08-11T00:00:00Z')
  })

  it('getScan URL-encodes the scan id', async () => {
    mockedApi.mockResolvedValueOnce({})
    await getScan('with/slash')
    expect(mockedApi).toHaveBeenCalledWith('/scan/with%2Fslash')
  })
})
