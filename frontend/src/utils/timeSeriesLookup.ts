export interface TimeSeriesPoint {
  time: number
}

export function createTimeLookup<T extends TimeSeriesPoint>(points: readonly T[]): Map<number, T> {
  const byTime = new Map<number, T>()
  for (const point of points) {
    if (Number.isFinite(point.time)) {
      byTime.set(point.time, point)
    }
  }
  return byTime
}

export function lookupByTime<T>(lookup: ReadonlyMap<number, T>, time: number): T | null {
  if (!Number.isFinite(time)) {
    return null
  }
  return lookup.get(time) ?? null
}
