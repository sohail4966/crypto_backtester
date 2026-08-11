import { describe, expect, it } from 'vitest'
import { buildBacktestMarkers } from '@/utils/backtestMarkers'

describe('buildBacktestMarkers', () => {
  it('maps buy/sell signals and trade entry/exit', () => {
    const markers = buildBacktestMarkers(
      [{ time: 100, side: 'buy' }],
      [
        {
          entryTime: 200,
          exitTime: 300,
          entryPrice: 1,
          exitPrice: 2,
          side: 'long',
          exitReason: 'signal',
          forcedClose: false,
          returnPct: 10,
          size: 1,
          commissionPaid: 0,
          pnlQuote: 1,
        },
      ],
      'dark',
    )

    expect(markers).toHaveLength(3)
    expect(markers[0]).toMatchObject({
      time: 100,
      shape: 'arrowUp',
      position: 'belowBar',
    })
    expect(markers[1]).toMatchObject({
      time: 200,
      shape: 'arrowUp',
      text: 'E',
    })
    expect(markers[2]).toMatchObject({
      time: 300,
      shape: 'circle',
      text: 'X',
    })
  })
})
