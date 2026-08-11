import { describe, expect, it } from 'vitest'
import {
  computeRiskReward,
  findHitDrawing,
  normalizeRectangleCorners,
} from '@/utils/drawingGeometry'
import type { Drawing } from '@/types/drawing'

describe('drawingGeometry', () => {
  it('normalizes rectangle corners regardless of click order', () => {
    const result = normalizeRectangleCorners(
      { time: 10, price: 50 },
      { time: 5, price: 100 },
    )
    expect(result.topLeft).toEqual({ time: 5, price: 100 })
    expect(result.bottomRight).toEqual({ time: 10, price: 50 })
  })

  it('computes risk/reward ratio', () => {
    const rr = computeRiskReward({
      id: '1',
      type: 'price_range',
      symbolId: 'BTC/USDT',
      timeframe: '1h',
      color: '#58a6ff',
      visible: true,
      createdAt: 1,
      entryPrice: 100,
      targetPrice: 120,
      stopPrice: 90,
    })
    expect(rr.risk).toBe(10)
    expect(rr.reward).toBe(20)
    expect(rr.ratio).toBe(2)
  })

  it('hit-tests horizontal lines within threshold', () => {
    const drawing: Drawing = {
      id: 'h',
      type: 'horizontal_line',
      symbolId: 'BTC/USDT',
      timeframe: '1h',
      color: '#58a6ff',
      visible: true,
      createdAt: 1,
      price: 100,
      lineWidth: 1,
      style: 'solid',
    }
    const hit = findHitDrawing([drawing], {
      x: 10,
      y: 52,
      timeToX: () => 10,
      priceToY: (price) => (price === 100 ? 50 : null),
    })
    expect(hit?.id).toBe('h')
  })
})
