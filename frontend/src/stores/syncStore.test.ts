import { beforeEach, describe, expect, it, vi } from 'vitest'
import { publishSync, resetSyncListeners, subscribeSync } from '@/stores/syncStore'

describe('syncStore pub/sub', () => {
  beforeEach(() => {
    resetSyncListeners()
  })

  it('delivers events to subscribers', () => {
    const listener = vi.fn()
    const unsub = subscribeSync(listener)
    publishSync({
      type: 'crosshair',
      sourcePaneId: 'a',
      time: 100,
    })
    expect(listener).toHaveBeenCalledWith({
      type: 'crosshair',
      sourcePaneId: 'a',
      time: 100,
    })
    unsub()
    publishSync({
      type: 'crosshair',
      sourcePaneId: 'a',
      time: 200,
    })
    expect(listener).toHaveBeenCalledTimes(1)
  })
})
