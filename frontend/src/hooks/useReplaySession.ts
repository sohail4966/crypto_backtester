import { useCallback, useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useToast } from '@/components/ui/Toast'
import {
  buildReplayWsUrl,
  createReplaySession,
  deleteReplaySession,
  getReplaySession,
} from '@/services/replayApi'
import { createReplayWsClient } from '@/services/replayWsClient'
import { useChartStore } from '@/stores/chartStore'
import { useIndicatorStore } from '@/stores/indicatorStore'
import { useReplayStore } from '@/stores/replayStore'
import type { IndicatorSpec, IndicatorSeriesMap } from '@/types/indicator'
import type { OHLCVBar } from '@/types/candle'
import type { ReplayServerEvent, ReplayTick } from '@/types/replay'
import { logReplayWsLifecycle } from '@/utils/replayWsLog'

export interface ReplayBaselineSnapshot {
  baselineCandles: OHLCVBar[]
  baselineIndicators: IndicatorSeriesMap
}

function visibleIndicatorSpecs(): IndicatorSpec[] {
  const active = useIndicatorStore.getState().active
  const seen = new Set<string>()
  const specs: IndicatorSpec[] = []
  for (const item of active) {
    if (item.visible === false) {
      continue
    }
    const id = `${item.key}:${JSON.stringify(item.params)}:${item.pane}`
    if (seen.has(id)) {
      continue
    }
    seen.add(id)
    specs.push({ key: item.key, params: item.params, pane: item.pane })
  }
  return specs
}

function normalizeTicks(event: Extract<ReplayServerEvent, { type: 'tick_batch' }>): ReplayTick[] {
  return event.ticks.map((tick) => ({
    bar: tick.bar,
    indicators: Object.fromEntries(
      Object.entries(tick.indicators).map(([key, value]) => [
        key,
        {
          time: (value as { time?: number }).time ?? tick.bar.time,
          value: (value as { value?: number | null }).value ?? null,
        },
      ]),
    ),
  }))
}

function shouldQueueTicks(): boolean {
  const { phase, serverState } = useReplayStore.getState()
  return (
    phase === 'playing' ||
    phase === 'buffer_loading' ||
    serverState === 'playing'
  )
}

function handleServerEvent(event: ReplayServerEvent, showToast: (message: string) => void) {
  const store = useReplayStore.getState()

  switch (event.type) {
    case 'replay_state':
      store.applyState({
        cursor: event.cursor,
        startAnchor:
          event.startAnchor ??
          (event as { start?: number }).start,
        latestAvailable: event.latestAvailable,
        queueRemaining: event.queueRemaining,
        state: event.state,
        speed: event.speed,
      })
      if (event.state === 'playing') {
        store.playLocally()
      } else if (event.state === 'completed') {
        store.setCompleted()
      } else if (event.state === 'paused') {
        const { phase } = useReplayStore.getState()
        // Ignore initial paused handshake before snapshot lands.
        if (phase === 'connecting') {
          break
        }
        // Honor explicit server pause only when client is actively playing.
        if (phase === 'playing' || phase === 'buffer_loading') {
          store.pauseLocally()
        }
      }
      break
    case 'snapshot':
      store.applySnapshot(event)
      break
    case 'tick_batch': {
      const ticks = normalizeTicks(event)
      if (ticks.length === 0) {
        logReplayWsLifecycle('tick_batch empty — server has no forward bars', {
          cursor: event.cursor,
          queueRemaining: event.queueRemaining,
        })
        if (event.queueRemaining === 0) {
          store.setCompleted()
        }
        break
      }
      if (shouldQueueTicks()) {
        store.enqueueBatch({ ...event, ticks })
        logReplayWsLifecycle(`queued ${ticks.length} ticks`, {
          queueDepth: useReplayStore.getState().tickQueue.length,
        })
      } else {
        for (const tick of ticks) {
          store.applyTick(tick)
        }
        if (event.cursor != null) {
          store.applyState({ cursor: event.cursor })
        }
        logReplayWsLifecycle(`applied ${ticks.length} ticks immediately`, {
          phase: useReplayStore.getState().phase,
        })
      }
      break
    }
    case 'buffer_loading':
      store.setBufferLoading(true)
      break
    case 'buffer_ready':
      store.setBufferLoading(false)
      if (event.latestAvailable != null) {
        store.applyState({ latestAvailable: event.latestAvailable })
      }
      break
    case 'buffer_reset':
      store.setBufferLoading(false)
      useReplayStore.setState({ tickQueue: [], phase: 'seeking' })
      break
    case 'replay_completed':
      store.setCompleted()
      break
    case 'error':
      if (event.code === 'SEEK_OUT_OF_RANGE') {
        showToast(event.message || 'Seek target is out of range')
        store.snapSeekToCursor()
      } else if (event.code !== 'SUPERSEDED') {
        showToast(event.message || event.code)
      }
      break
    default:
      break
  }
}

async function teardownSession(sessionId: string | null) {
  if (!sessionId) {
    return
  }
  try {
    await deleteReplaySession(sessionId)
  } catch {
    // session may already be gone
  }
}

export function useReplaySession() {
  const { showToast } = useToast()
  const [searchParams, setSearchParams] = useSearchParams()
  const replayMode = useChartStore((state) => state.replayMode)
  const symbol = useChartStore((state) => state.symbol)
  const timeframe = useChartStore((state) => state.timeframe)
  const phase = useReplayStore((state) => state.phase)
  const sessionId = useReplayStore((state) => state.sessionId)
  const serverState = useReplayStore((state) => state.serverState)
  const activeIndicators = useIndicatorStore((state) => state.active)

  const wsRef = useRef<ReturnType<typeof createReplayWsClient> | null>(null)
  const indicatorSpecsRef = useRef<string | null>(null)
  const resumeAttemptedRef = useRef(false)
  const startInFlightRef = useRef(false)
  const symbolRef = useRef(symbol?.id)
  const timeframeRef = useRef(timeframe)

  const connectWs = useCallback(
    (wsUrl: string, nextSessionId: string) => {
      wsRef.current?.disconnect()
      const client = createReplayWsClient(buildReplayWsUrl(wsUrl))
      wsRef.current = client
      useReplayStore.getState().attachWsClient(client)
      useReplayStore.getState().setConnectionStatus('disconnected')

      client.onEvent((event) => handleServerEvent(event, showToast))
      client.onOpen(() => {
        useReplayStore.getState().setConnectionStatus('connected')
      })
      client.onClose((code, reason) => {
        const store = useReplayStore.getState()
        if (code === 4404) {
          store.setConnectionStatus('not_found', 'Session not found')
          showToast('Replay session not found')
        } else if (code === 4401 || reason.includes('SUPERSEDED')) {
          store.setConnectionStatus('superseded', 'Opened in another tab')
          store.pauseLocally()
        } else if (code !== 1000) {
          store.setConnectionStatus('error', reason || 'Connection closed')
        } else {
          store.setConnectionStatus('disconnected')
        }
      })

      client.connect()
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev)
          next.set('replaySession', nextSessionId)
          return next
        },
        { replace: true },
      )
    },
    [setSearchParams, showToast],
  )

  const startSessionAt = useCallback(
    async (start: number, baseline?: ReplayBaselineSnapshot) => {
      if (!symbol || startInFlightRef.current) {
        return
      }
      startInFlightRef.current = true
      resumeAttemptedRef.current = true
      const existingId = useReplayStore.getState().sessionId
      await teardownSession(existingId)
      useReplayStore.getState().resetSession()
      if (baseline) {
        useReplayStore.getState().setReplayBaseline(
          baseline.baselineCandles,
          baseline.baselineIndicators,
        )
      }

      try {
        const response = await createReplaySession({
          symbol: symbol.ticker,
          timeframe,
          start,
          indicators: visibleIndicatorSpecs(),
          speed: useReplayStore.getState().speed,
        })
        useReplayStore.getState().setConnecting(response.sessionId)
        connectWs(response.wsUrl, response.sessionId)
        indicatorSpecsRef.current = JSON.stringify(visibleIndicatorSpecs())
      } catch (error) {
        useReplayStore.getState().setPhase('error')
        showToast(error instanceof Error ? error.message : 'Failed to create replay session')
      } finally {
        startInFlightRef.current = false
      }
    },
    [connectWs, showToast, symbol, timeframe],
  )

  const stopSession = useCallback(async () => {
    const id = useReplayStore.getState().sessionId
    wsRef.current?.disconnect()
    wsRef.current = null
    await teardownSession(id)
    useReplayStore.getState().resetSession()
    indicatorSpecsRef.current = null
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        next.delete('replaySession')
        return next
      },
      { replace: true },
    )
    if (useChartStore.getState().replayMode) {
      useReplayStore.getState().enterPickAnchor()
    }
  }, [setSearchParams])

  const resumeSession = useCallback(
    async (id: string) => {
      try {
        const state = await getReplaySession(id)
        useChartStore.getState().setReplayMode(true)
        useReplayStore.getState().setConnecting(id)
        useReplayStore.getState().applyState(state)
        connectWs(`/ws/replay/${id}`, id)
        indicatorSpecsRef.current = JSON.stringify(visibleIndicatorSpecs())
      } catch (error) {
        showToast(error instanceof Error ? error.message : 'Failed to resume replay session')
        setSearchParams(
          (prev) => {
            const next = new URLSearchParams(prev)
            next.delete('replaySession')
            return next
          },
          { replace: true },
        )
        if (useChartStore.getState().replayMode) {
          useReplayStore.getState().enterPickAnchor()
        }
      }
    },
    [connectWs, setSearchParams, showToast],
  )

  useEffect(() => {
    const urlSession = searchParams.get('replaySession')
    if (urlSession && !resumeAttemptedRef.current && !sessionId) {
      resumeAttemptedRef.current = true
      void resumeSession(urlSession)
    }
  }, [resumeSession, searchParams, sessionId])

  useEffect(() => {
    if (replayMode) {
      if (phase === 'inactive' && !searchParams.get('replaySession')) {
        useReplayStore.getState().enterPickAnchor()
      }
      return
    }

    resumeAttemptedRef.current = false
    if (sessionId) {
      void stopSession()
    } else {
      useReplayStore.getState().setInactive()
    }
  }, [replayMode, phase, searchParams, sessionId, stopSession])

  useEffect(() => {
    const symbolId = symbol?.id
    const prevSymbol = symbolRef.current
    const prevTimeframe = timeframeRef.current
    symbolRef.current = symbolId
    timeframeRef.current = timeframe

    if (!sessionId) {
      return
    }
    if (symbolId === prevSymbol && timeframe === prevTimeframe) {
      return
    }
    void stopSession()
  }, [sessionId, stopSession, symbol?.id, timeframe])

  useEffect(() => {
    const specs = visibleIndicatorSpecs()
    const key = JSON.stringify(specs)
    if (!sessionId || phase === 'inactive' || phase === 'pick_anchor' || phase === 'connecting') {
      indicatorSpecsRef.current = key
      return
    }
    if (indicatorSpecsRef.current === null) {
      indicatorSpecsRef.current = key
      return
    }
    if (indicatorSpecsRef.current === key) {
      return
    }
    indicatorSpecsRef.current = key

    const client = wsRef.current
    if (!client?.isOpen()) {
      return
    }

    if (serverState === 'playing') {
      useReplayStore.getState().pauseLocally()
      client.send({ action: 'pause' })
    }

    client.send({ action: 'set_indicators', indicators: specs })
  }, [activeIndicators, phase, serverState, sessionId])

  useEffect(() => {
    if (phase !== 'pick_anchor') {
      return
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        useReplayStore.getState().setInactive()
        useChartStore.getState().setReplayMode(false)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [phase])

  return {
    startSessionAt,
    stopSession,
    sendCommand: (command: Parameters<NonNullable<typeof wsRef.current>['send']>[0]) => {
      wsRef.current?.send(command)
    },
  }
}
