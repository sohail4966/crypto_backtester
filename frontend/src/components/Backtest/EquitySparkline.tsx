import { useMemo } from 'react'
import type { EquityPoint } from '@/types/backtest'

interface EquitySparklineProps {
  points: EquityPoint[]
  className?: string
}

/** Lightweight SVG equity curve for backtest results (FE-007). */
export function EquitySparkline({ points, className }: EquitySparklineProps) {
  const path = useMemo(() => {
    if (points.length < 2) {
      return null
    }
    const values = points.map((p) => p.equity)
    const min = Math.min(...values)
    const max = Math.max(...values)
    const span = max - min || 1
    const w = 320
    const h = 80
    const coords = points.map((p, i) => {
      const x = (i / (points.length - 1)) * w
      const y = h - ((p.equity - min) / span) * (h - 4) - 2
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    return `M ${coords.join(' L ')}`
  }, [points])

  if (!path) {
    return (
      <p className="text-xs text-text-secondary">No equity series in this run.</p>
    )
  }

  return (
    <svg
      viewBox="0 0 320 80"
      className={className ?? 'h-20 w-full max-w-md text-accent'}
      role="img"
      aria-label="Equity curve"
    >
      <path d={path} fill="none" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  )
}
