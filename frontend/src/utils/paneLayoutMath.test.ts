import { describe, expect, it } from 'vitest'
import {
  computeMainPaneHeight,
  nextSubHeightAfterMainResize,
  nextSubPairHeightsAfterResize,
} from '@/utils/paneLayoutMath'

describe('paneLayoutMath', () => {
  it('shrinks sub and frees main space when dragging down', () => {
    const next = nextSubHeightAfterMainResize(112, 20, 400)
    expect(next).toBe(92)
  })

  it('grows sub only when main has room', () => {
    const next = nextSubHeightAfterMainResize(112, -50, 200)
    expect(next).toBe(132)
  })

  it('stops sub growth when main is at minimum', () => {
    const next = nextSubHeightAfterMainResize(112, -80, 180)
    expect(next).toBeNull()
  })

  it('redistributes height between two sub-panes', () => {
    const next = nextSubPairHeightsAfterResize(100, 100, 30)
    expect(next).toEqual({ top: 130, bottom: 70 })
  })

  it('computes main height from layout minus sub blocks', () => {
    const main = computeMainPaneHeight(600, ['rsi'], { rsi: 112 })
    expect(main).toBe(600 - 112 - 36 - 10)
  })

  it('keeps tab overhead for hidden sub-panes but excludes their chart height', () => {
    const main = computeMainPaneHeight(600, ['rsi', 'macd'], { rsi: 112, macd: 112 }, ['rsi'])
    expect(main).toBe(600 - 112 - 2 * (36 + 10))
  })
})
