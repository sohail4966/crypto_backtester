import { describe, expect, it } from 'vitest'
import {
  composeReplayCandles,
  filterCandlesBefore,
  mergeReplayIndicators,
} from '@/utils/replayChartData'

describe('replayChartData', () => {
  it('keeps live candles visible while the session connects', () => {
    const live = [
      { time: 100, open: 1, high: 2, low: 1, close: 2, volume: 1 },
      { time: 200, open: 2, high: 3, low: 2, close: 3, volume: 1 },
    ]

    expect(composeReplayCandles(true, live, [], [])).toEqual(live)
  })

  it('uses baseline as soon as it exists, even before WS session is active', () => {
    const live = [
      { time: 100, open: 1, high: 2, low: 1, close: 2, volume: 1 },
      { time: 200, open: 2, high: 3, low: 2, close: 3, volume: 1 },
    ]
    const baseline = [live[0]]

    expect(composeReplayCandles(false, live, baseline, [])).toEqual(baseline)
  })

  it('composes frozen baseline with newly revealed replay bars', () => {
    const baseline = [{ time: 100, open: 1, high: 2, low: 1, close: 2, volume: 1 }]
    const revealed = [{ time: 200, open: 2, high: 3, low: 2, close: 3, volume: 1 }]

    expect(composeReplayCandles(true, [], baseline, revealed)).toEqual([...baseline, ...revealed])
  })

  it('filters pre-anchor candles for baseline freeze', () => {
    const candles = [
      { time: 100, open: 1, high: 2, low: 1, close: 2, volume: 1 },
      { time: 200, open: 2, high: 3, low: 2, close: 3, volume: 1 },
    ]

    expect(filterCandlesBefore(200, candles)).toEqual([candles[0]])
  })

  it('merges baseline and revealed indicator points by time', () => {
    const merged = mergeReplayIndicators(
      { EMA_20: [{ time: 100, value: 1 }] },
      { EMA_20: [{ time: 200, value: 2 }] },
    )

    expect(merged.EMA_20).toEqual([
      { time: 100, value: 1 },
      { time: 200, value: 2 },
    ])
  })
})
