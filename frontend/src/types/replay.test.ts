import { describe, expect, it } from 'vitest'
import { replayProgress } from '@/types/replay'

describe('replayProgress', () => {
  it('returns zero when inputs are missing', () => {
    expect(replayProgress(null, 100, 200)).toBe(0)
  })

  it('computes progress against latest available', () => {
    expect(replayProgress(150, 100, 200)).toBeCloseTo(0.5)
  })

  it('clamps to one when cursor reaches latest', () => {
    expect(replayProgress(200, 100, 200)).toBe(1)
  })

  it('slows visually when latest available grows', () => {
    expect(replayProgress(150, 100, 300)).toBeCloseTo(0.25)
  })
})
