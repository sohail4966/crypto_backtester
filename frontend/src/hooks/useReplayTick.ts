import { useEffect, useRef } from 'react'
import { REPLAY_REFILL_THRESHOLD, replayIntervalMs } from '@/constants/replay'
import type { ReplayWsClient } from '@/services/replayWsClient'
import { useReplayStore } from '@/stores/replayStore'

interface UseReplayTickOptions {
  getWsClient: () => ReplayWsClient | null
}

export function useReplayTick({ getWsClient }: UseReplayTickOptions): void {
  const phase = useReplayStore((s) => s.phase)
  const speed = useReplayStore((s) => s.speed)
  const refillSentRef = useRef(false)

  useEffect(() => {
    if (phase !== 'playing') {
      refillSentRef.current = false
      return
    }

    const intervalMs = replayIntervalMs(speed)
    const id = window.setInterval(() => {
      const store = useReplayStore.getState()
      if (store.phase !== 'playing') {
        return
      }
      store.drainOne()

      const queueLen = useReplayStore.getState().tickQueue.length
      if (queueLen < REPLAY_REFILL_THRESHOLD) {
        if (!refillSentRef.current || queueLen === 0) {
          getWsClient()?.send({ action: 'refill' })
          refillSentRef.current = true
        }
      } else {
        refillSentRef.current = false
      }
    }, intervalMs)

    return () => {
      window.clearInterval(id)
    }
  }, [phase, speed, getWsClient])

  // Reset refill gate when queue recovers above threshold
  const queueLength = useReplayStore((s) => s.tickQueue.length)
  useEffect(() => {
    if (queueLength >= REPLAY_REFILL_THRESHOLD) {
      refillSentRef.current = false
    }
  }, [queueLength])
}
