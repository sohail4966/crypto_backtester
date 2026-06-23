import type { UTCTimestamp } from 'lightweight-charts'

export function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value)
}

export function toUtcTimestamp(time: number): UTCTimestamp | null {
  if (!Number.isInteger(time) || time < 0) {
    return null
  }
  return time as UTCTimestamp
}
