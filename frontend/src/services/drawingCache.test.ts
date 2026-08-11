import { beforeEach, describe, expect, it } from 'vitest'
import { del as idbDel, set as idbSet } from 'idb-keyval'
import { DRAWINGS_CACHE_KEY } from '@/constants/drawings'
import {
  isValidDrawing,
  readDrawingsCache,
  writeDrawingsCache,
} from '@/services/drawingCache'
import type { Drawing } from '@/types/drawing'

const sample: Drawing = {
  id: 'd1',
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

describe('drawingCache', () => {
  beforeEach(async () => {
    await idbDel(DRAWINGS_CACHE_KEY)
  })

  it('round-trips valid drawings', async () => {
    await writeDrawingsCache([sample])
    const cache = await readDrawingsCache()
    expect(cache?.drawings).toEqual([sample])
    expect(cache?.version).toBe(1)
  })

  it('rejects CSS var colors', () => {
    expect(
      isValidDrawing({
        ...sample,
        color: 'var(--color-accent)',
      }),
    ).toBe(false)
  })

  it('discards corrupt blobs', async () => {
    await idbSet(DRAWINGS_CACHE_KEY, { version: 1, drawings: [{ bad: true }], savedAt: 'x' })
    const cache = await readDrawingsCache()
    expect(cache).toBeNull()
  })
})
