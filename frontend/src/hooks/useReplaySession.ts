import { useCallback, useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { REPLAY_SESSION_QUERY } from '@/constants/replay'
import {
  createReplaySession,
  deleteReplaySession,
  getReplaySession,
} from '@/services/replayApi'
import type { ReplayWsClient } from '@/services/replayWsClient'
import { useChartStore } from '@/stores/chartStore'
import { useIndicatorStore } from '@/stores/indicatorStore'
import { useReplayStore } from '@/stores/replayStore'
import { useToast } from '@/components/ui/Toast'
import { visibleIndicatorSpecs } from '@/utils/replayIndicators'
import type { ReplaySpeed } from '@/types/replay'

export interface ReplaySessionApi {
  startFromAnchor: (startUnix: number) => Promise<void>
  stopToPickAnchor: () => Promise<void>
  teardownFully: () => Promise<void>
  play: () => void
  pause: () => void
  step: () => void
  seek: (to: number) => void
  setSpeed: (speed: ReplaySpeed) => void
  sendSetIndicators: () => void
  getWsClient: () => ReplayWsClient | null
  registerWsClient: (client: ReplayWsClient | null) => void
  onUnauthorized: () => void
}

/**
 * Orchestrates create / resume / teardown and exposes control helpers.
 * WS client instance is owned by useReplayWs but registered here for commands.
 */
export function useReplaySession(): ReplaySessionApi {
  const { showToast } = useToast()
  const [searchParams, setSearchParams] = useSearchParams()
  const wsClientRef = useRef<ReplayWsClient | null>(null)
  const resumeAttemptedRef = useRef<string | null>(null)
  const tearingDownRef = useRef(false)

  const symbol = useChartStore((s) => s.symbol)
  const timeframe = useChartStore((s) => s.timeframe)
  const replayMode = useChartStore((s) => s.replayMode)
  const setReplayMode = useChartStore((s) => s.setReplayMode)

  const writeSessionParam = useCallback(
    (sessionId: string | null) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev)
          if (sessionId) {
            next.set(REPLAY_SESSION_QUERY, sessionId)
          } else {
            next.delete(REPLAY_SESSION_QUERY)
          }
          return next
        },
        { replace: true },
      )
    },
    [setSearchParams],
  )

  const registerWsClient = useCallback((client: ReplayWsClient | null) => {
    wsClientRef.current = client
  }, [])

  const getWsClient = useCallback(() => wsClientRef.current, [])

  const onUnauthorized = useCallback(() => {
    resumeAttemptedRef.current = null
    writeSessionParam(null)
    useReplayStore.getState().reset()
    setReplayMode(false)
  }, [setReplayMode, writeSessionParam])

  const closeWs = useCallback(() => {
    wsClientRef.current?.close()
    wsClientRef.current = null
  }, [])

  const stopToPickAnchor = useCallback(async () => {
    if (tearingDownRef.current) {
      return
    }
    tearingDownRef.current = true
    try {
      const sessionId = useReplayStore.getState().sessionId
      wsClientRef.current?.send({ action: 'pause' })
      closeWs()
      if (sessionId) {
        try {
          await deleteReplaySession(sessionId)
        } catch {
          // Best-effort
        }
      }
      writeSessionParam(null)
      useReplayStore.getState().resetToPickAnchor()
      setReplayMode(true)
    } finally {
      tearingDownRef.current = false
    }
  }, [closeWs, setReplayMode, writeSessionParam])

  const teardownFully = useCallback(async () => {
    if (tearingDownRef.current) {
      return
    }
    tearingDownRef.current = true
    try {
      const sessionId = useReplayStore.getState().sessionId
      wsClientRef.current?.send({ action: 'pause' })
      closeWs()
      if (sessionId) {
        try {
          await deleteReplaySession(sessionId)
        } catch {
          // Best-effort
        }
      }
      writeSessionParam(null)
      useReplayStore.getState().reset()
      setReplayMode(false)
    } finally {
      tearingDownRef.current = false
    }
  }, [closeWs, setReplayMode, writeSessionParam])

  const startFromAnchor = useCallback(
    async (startUnix: number) => {
      const sym = useChartStore.getState().symbol
      if (!sym) {
        showToast('Select a symbol before starting replay')
        return
      }
      const speed = useReplayStore.getState().speed
      const indicators = visibleIndicatorSpecs(useIndicatorStore.getState().active)

      useReplayStore.getState().beginConnect('pending', '')
      try {
        const created = await createReplaySession({
          symbol: sym.id,
          timeframe: useChartStore.getState().timeframe,
          start: startUnix,
          indicators,
          speed,
          autoplay: false,
        })
        useReplayStore.getState().beginConnect(created.sessionId, created.wsUrl)
        writeSessionParam(created.sessionId)
        setReplayMode(true)
      } catch (error) {
        const message =
          error instanceof Error ? error.message : 'Failed to create replay session'
        useReplayStore.getState().setError(message)
        showToast(message)
        useReplayStore.getState().resetToPickAnchor()
      }
    },
    [setReplayMode, showToast, writeSessionParam],
  )

  const play = useCallback(() => {
    const store = useReplayStore.getState()
    if (store.phase === 'completed') {
      return
    }
    store.clearExpectImmediateTicks()
    store.setForcePausedUntilPlay(false)
    const client = wsClientRef.current
    const open = client?.readyState === WebSocket.OPEN
    // Don't claim playing until the socket can accept (or queue) the command.
    store.setPhase(open ? 'playing' : 'connecting')
    const speed = store.speed
    client?.send({ action: 'play', speed })
    if (!open && client) {
      // Queued; flip to playing once open flush happens via first server state / onOpen.
      // Local UX: leave connecting until replay_state or open confirms.
    }
  }, [])

  const pause = useCallback(() => {
    const store = useReplayStore.getState()
    store.clearExpectImmediateTicks()
    store.setPhase('paused')
    wsClientRef.current?.send({ action: 'pause' })
  }, [])

  const step = useCallback(() => {
    const store = useReplayStore.getState()
    if (store.phase === 'completed' || store.phase === 'connecting') {
      return
    }
    store.markExpectImmediateTicks()
    wsClientRef.current?.send({ action: 'step', count: 1 })
  }, [])

  const seek = useCallback((to: number) => {
    const store = useReplayStore.getState()
    store.beginSeeking()
    wsClientRef.current?.send({ action: 'seek', to })
  }, [])

  const setSpeed = useCallback((speed: ReplaySpeed) => {
    useReplayStore.getState().setSpeed(speed)
    wsClientRef.current?.send({ action: 'set_speed', speed })
  }, [])

  const sendSetIndicators = useCallback(() => {
    const specs = visibleIndicatorSpecs(useIndicatorStore.getState().active)
    const store = useReplayStore.getState()
    store.setForcePausedUntilPlay(true)
    store.setPhase('paused')
    wsClientRef.current?.send({ action: 'pause' })
    wsClientRef.current?.send({ action: 'set_indicators', indicators: specs })
  }, [])

  // URL resume on mount / when query appears — reconnect if WS missing (FE-008)
  useEffect(() => {
    const sessionFromUrl = searchParams.get(REPLAY_SESSION_QUERY)
    if (!sessionFromUrl) {
      resumeAttemptedRef.current = null
      return
    }

    const store = useReplayStore.getState()
    const existing = store.sessionId
    const phase = store.phase
    const wsOpen = wsClientRef.current?.readyState === WebSocket.OPEN

    // Already owning this session: do not re-fetch (avoids racing create → URL write).
    // If the socket was torn down (route remount), re-issue beginConnect so useReplayWs reconnects.
    if (existing === sessionFromUrl && phase !== 'inactive') {
      resumeAttemptedRef.current = sessionFromUrl
      if (!wsOpen) {
        const wsUrl = store.wsUrl ?? `/ws/replay/${sessionFromUrl}`
        if (store.wsUrl !== wsUrl || store.connection === 'closed' || store.connection === 'red') {
          useReplayStore.getState().beginConnect(sessionFromUrl, wsUrl)
        }
      }
      return
    }

    if (resumeAttemptedRef.current === sessionFromUrl) {
      return
    }

    resumeAttemptedRef.current = sessionFromUrl
    let cancelled = false

    async function resume() {
      try {
        const meta = await getReplaySession(sessionFromUrl!)
        if (cancelled) {
          return
        }
        setReplayMode(true)
        const wsUrl = `/ws/replay/${meta.sessionId}`
        useReplayStore.getState().beginConnect(meta.sessionId, wsUrl)
        useReplayStore.getState().applyReplayState(meta)
        if (meta.serverState === 'completed') {
          useReplayStore.getState().setPhase('completed')
        } else {
          useReplayStore.getState().setPhase('paused')
        }
      } catch {
        if (cancelled) {
          return
        }
        showToast('Replay session not found')
        writeSessionParam(null)
        useReplayStore.getState().reset()
        setReplayMode(false)
      }
    }

    void resume()
    return () => {
      cancelled = true
    }
  }, [searchParams, setReplayMode, showToast, writeSessionParam])

  // Symbol / timeframe change → teardown session, stay in pick_anchor if mode on
  const prevSymbolTfRef = useRef(`${symbol?.id ?? ''}:${timeframe}`)
  useEffect(() => {
    const key = `${symbol?.id ?? ''}:${timeframe}`
    const prev = prevSymbolTfRef.current
    prevSymbolTfRef.current = key
    if (prev === key) {
      return
    }
    const store = useReplayStore.getState()
    if (!store.sessionId && store.phase === 'inactive') {
      return
    }
    if (!store.sessionId && store.phase === 'pick_anchor') {
      return
    }
    if (!store.sessionId && store.phase !== 'connecting') {
      return
    }

    void (async () => {
      const sessionId = useReplayStore.getState().sessionId
      closeWs()
      if (sessionId && sessionId !== 'pending') {
        try {
          await deleteReplaySession(sessionId)
        } catch {
          // best-effort
        }
      }
      writeSessionParam(null)
      if (useChartStore.getState().replayMode) {
        useReplayStore.getState().resetToPickAnchor()
      } else {
        useReplayStore.getState().reset()
      }
    })()
  }, [symbol?.id, timeframe, closeWs, writeSessionParam])

  // Keep replayMode in sync when entering pick via store alone
  useEffect(() => {
    if (!replayMode) {
      return
    }
    const phase = useReplayStore.getState().phase
    if (phase === 'inactive') {
      useReplayStore.getState().enterPickAnchor()
    }
  }, [replayMode])

  return {
    startFromAnchor,
    stopToPickAnchor,
    teardownFully,
    play,
    pause,
    step,
    seek,
    setSpeed,
    sendSetIndicators,
    getWsClient,
    registerWsClient,
    onUnauthorized,
  }
}
