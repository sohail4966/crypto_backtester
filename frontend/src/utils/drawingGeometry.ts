import type { ChartPoint, Drawing, PriceRangeDrawing } from '@/types/drawing'
import { DRAWING_HIT_THRESHOLD_PX } from '@/constants/drawings'

export function normalizeRectangleCorners(
  a: ChartPoint,
  b: ChartPoint,
): { topLeft: ChartPoint; bottomRight: ChartPoint } {
  const minTime = Math.min(a.time, b.time)
  const maxTime = Math.max(a.time, b.time)
  const maxPrice = Math.max(a.price, b.price)
  const minPrice = Math.min(a.price, b.price)
  return {
    topLeft: { time: minTime, price: maxPrice },
    bottomRight: { time: maxTime, price: minPrice },
  }
}

export interface RiskReward {
  risk: number
  reward: number
  ratio: number | null
}

export function computeRiskReward(drawing: PriceRangeDrawing): RiskReward {
  const risk = Math.abs(drawing.entryPrice - drawing.stopPrice)
  const reward = Math.abs(drawing.targetPrice - drawing.entryPrice)
  if (risk === 0) {
    return { risk, reward, ratio: null }
  }
  return { risk, reward, ratio: reward / risk }
}

export function formatRiskReward(drawing: PriceRangeDrawing): string {
  const { risk, reward, ratio } = computeRiskReward(drawing)
  if (ratio == null || !Number.isFinite(ratio)) {
    return `R ${risk.toFixed(2)} / Rew ${reward.toFixed(2)}`
  }
  return `R:R ${ratio.toFixed(2)} (risk ${risk.toFixed(2)})`
}

function distPointToSegment(
  px: number,
  py: number,
  x1: number,
  y1: number,
  x2: number,
  y2: number,
): number {
  const dx = x2 - x1
  const dy = y2 - y1
  if (dx === 0 && dy === 0) {
    return Math.hypot(px - x1, py - y1)
  }
  const t = Math.max(0, Math.min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
  return Math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))
}

export interface HitTestCoords {
  x: number
  y: number
  timeToX: (time: number) => number | null
  priceToY: (price: number) => number | null
}

export function hitTestDrawing(
  drawing: Drawing,
  coords: HitTestCoords,
  threshold = DRAWING_HIT_THRESHOLD_PX,
): boolean {
  const { x, y, timeToX, priceToY } = coords

  switch (drawing.type) {
    case 'horizontal_line': {
      const py = priceToY(drawing.price)
      return py != null && Math.abs(y - py) <= threshold
    }
    case 'trend_line': {
      const x1 = timeToX(drawing.p1.time)
      const y1 = priceToY(drawing.p1.price)
      const x2 = timeToX(drawing.p2.time)
      const y2 = priceToY(drawing.p2.price)
      if (x1 == null || y1 == null || x2 == null || y2 == null) {
        return false
      }
      return distPointToSegment(x, y, x1, y1, x2, y2) <= threshold
    }
    case 'rectangle': {
      const x1 = timeToX(drawing.topLeft.time)
      const y1 = priceToY(drawing.topLeft.price)
      const x2 = timeToX(drawing.bottomRight.time)
      const y2 = priceToY(drawing.bottomRight.price)
      if (x1 == null || y1 == null || x2 == null || y2 == null) {
        return false
      }
      const left = Math.min(x1, x2)
      const right = Math.max(x1, x2)
      const top = Math.min(y1, y2)
      const bottom = Math.max(y1, y2)
      return x >= left - threshold && x <= right + threshold && y >= top - threshold && y <= bottom + threshold
    }
    case 'price_range': {
      for (const price of [drawing.entryPrice, drawing.targetPrice, drawing.stopPrice]) {
        const py = priceToY(price)
        if (py != null && Math.abs(y - py) <= threshold) {
          return true
        }
      }
      return false
    }
    case 'text_note': {
      const tx = timeToX(drawing.anchorTime)
      const ty = priceToY(drawing.anchorPrice)
      if (tx == null || ty == null) {
        return false
      }
      return Math.hypot(x - tx, y - ty) <= threshold * 3
    }
    default:
      return false
  }
}

export function findHitDrawing(
  drawings: Drawing[],
  coords: HitTestCoords,
): Drawing | null {
  for (let i = drawings.length - 1; i >= 0; i -= 1) {
    const drawing = drawings[i]
    if (!drawing || !drawing.visible) {
      continue
    }
    if (hitTestDrawing(drawing, coords)) {
      return drawing
    }
  }
  return null
}
