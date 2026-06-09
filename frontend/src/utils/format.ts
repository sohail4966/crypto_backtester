export function formatPrice(value: number, decimals = 2): string {
  return value.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

export function formatVolume(value: number): string {
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(2)}M`
  }
  if (value >= 1_000) {
    return `${(value / 1_000).toFixed(1)}K`
  }
  return value.toLocaleString('en-US', { maximumFractionDigits: 0 })
}

export function formatChange(open: number, close: number): {
  delta: string
  percent: string
  isUp: boolean
} {
  const change = close - open
  const percent = open === 0 ? 0 : (change / open) * 100
  const isUp = change >= 0
  const sign = isUp ? '+' : ''
  return {
    delta: `${sign}${formatPrice(change)}`,
    percent: `${sign}${percent.toFixed(2)}%`,
    isUp,
  }
}
