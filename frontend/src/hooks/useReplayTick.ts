import { useCallback, useEffect, useRef } from 'react'
import {
  REPLAY_BUFFER_LOADING_TIMEOUT_MS,
  REPLAY_TICK_REFILL_THRESHOLD,
  replayIntervalMs,
} from '@/types/replay'
import { useReplayStore } from '@/stores/replayStore'

interface UseReplayTickOptions {
  sendRefill: () => void
  onCursorAdvanced?: (cursor: number) => void
}

export function useReplayTick({
  sendRefill,
  onCursorAdvanced,
}: UseReplayTickOptions) {
  const phase = useReplayStore((state) => state.phase)
  const speed = useReplayStore((state) => state.speed)
  const bufferLoading = useReplayStore((state) => state.bufferLoading)
  const playingRef = useRef(false)
  const lastRefillAtRef = useRef(0)
  const stallRecoveryAtRef = useRef(0)

  const requestRefill = useCallback(() => {
    const { serverState, phase } = useReplayStore.getState()
    if (serverState === 'completed' || phase === 'completed') {
      return
    }
    const now = Date.now()
    if (now - lastRefillAtRef.current < 500) {
      return
    }
    lastRefillAtRef.current = now
    sendRefill()
  }, [sendRefill])

  const requestStallRecovery = useCallback(() => {
    const { tickQueue, phase, serverState } = useReplayStore.getState()
    if (phase !== 'playing' || serverState !== 'playing' || tickQueue.length > 0) {
      return
    }
    const now = Date.now()
    if (now - stallRecoveryAtRef.current < 1000) {
      return
    }
    stallRecoveryAtRef.current = now
    sendRefill()
  }, [sendRefill])

  // Buffer loading timeout fallback
  useEffect(() => {
    if (!bufferLoading) {
      return
    }
    const timeout = window.setTimeout(() => {
      useReplayStore.getState().setBufferLoading(false)
    }, REPLAY_BUFFER_LOADING_TIMEOUT_MS)
    return () => window.clearTimeout(timeout)
  }, [bufferLoading])

  useEffect(() => {
    playingRef.current = phase === 'playing'
    if (phase !== 'playing') {
      return
    }

    const intervalMs = replayIntervalMs(speed)
    const timer = window.setInterval(() => {
      if (!playingRef.current) {
        return
      }

      const store = useReplayStore.getState()
      if (store.bufferLoading) {
        return
      }

      let tick = store.shiftTick()
      if (!tick) {
        requestStallRecovery()
        requestRefill()
        return
      }

      store.applyTick(tick)
      onCursorAdvanced?.(tick.bar.time)

      const remaining = useReplayStore.getState().tickQueue.length
      if (remaining < REPLAY_TICK_REFILL_THRESHOLD) {
        requestRefill()
      }
    }, intervalMs)

    return () => window.clearInterval(timer)
  }, [onCursorAdvanced, phase, requestRefill, requestStallRecovery, speed])
}
