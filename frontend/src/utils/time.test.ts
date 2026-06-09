import { describe, expect, it } from 'vitest'
import { chartWindowFromDataRange, shiftUnixByBars } from '@/utils/time'

describe('chartWindowFromDataRange', () => {
  it('anchors the window on latest stored bar', () => {
    const latest = 1_700_000_000
    const window = chartWindowFromDataRange(
      {
        symbolId: 'BTC/USDT',
        timeframe: '1h',
        earliest: latest - 10_000 * 3600,
        latest,
        barCount: 10_000,
      },
      500,
      '1h',
    )

    expect(window).toEqual({
      start: latest - 499 * 3600,
      end: latest,
    })
  })

  it('clamps start to earliest when history is shorter than chunk', () => {
    const earliest = 1_700_000_000
    const latest = earliest + 120 * 60
    const window = chartWindowFromDataRange(
      {
        symbolId: 'SOL/USDT',
        timeframe: '1m',
        earliest,
        latest,
        barCount: 121,
      },
      500,
      '1m',
    )

    expect(window).toEqual({ start: earliest, end: latest })
  })

  it('returns null when metadata has no latest anchor', () => {
    expect(
      chartWindowFromDataRange(
        {
          symbolId: 'BTC/USDT',
          timeframe: '1h',
          earliest: null,
          latest: null,
          barCount: 0,
        },
        500,
        '1h',
      ),
    ).toBeNull()
  })
})

describe('shiftUnixByBars', () => {
  it('moves timestamps backward by bar count', () => {
    expect(shiftUnixByBars(3600, '1m', 5)).toBe(3600 - 5 * 60)
  })
})
