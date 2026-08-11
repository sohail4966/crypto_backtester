import { useEffect, useRef } from 'react'
import {
  REPLAY_BUFFER_UI_TIMEOUT_MS,
} from '@/constants/replay'
import { notifyAuthFailure } from '@/services/authSession'
import { ReplayWsClient } from '@/services/replayWsClient'
import { useReplayStore } from '@/stores/replayStore'
import { useToast } from '@/components/ui/Toast'
import type { ReplayWsInbound } from '@/types/replay'

interface UseReplayWsOptions {
  registerWsClient: (client: ReplayWsClient | null) => void
  onSuperseded?: () => void
  onNotFound?: () => void
}

export function useReplayWs({
  registerWsClient,
  onSuperseded,
  onNotFound,
}: UseReplayWsOptions): void {
  const { showToast } = useToast()
  const clientRef = useRef<ReplayWsClient | null>(null)
  const bufferTimerRef = useRef<number | null>(null)

  const sessionId = useReplayStore((s) => s.sessionId)
  const wsUrl = useReplayStore((s) => s.wsUrl)

  useEffect(() => {
    return () => {
      if (bufferTimerRef.current != null) {
        window.clearTimeout(bufferTimerRef.current)
      }
    }
  }, [])

  useEffect(() => {
    if (!sessionId || sessionId === 'pending' || !wsUrl) {
      if (clientRef.current) {
        clientRef.current.close()
        clientRef.current = null
        registerWsClient(null)
      }
      return
    }

    const client = new ReplayWsClient()
    clientRef.current = client
    registerWsClient(client)

    const clearBufferTimer = () => {
      if (bufferTimerRef.current != null) {
        window.clearTimeout(bufferTimerRef.current)
        bufferTimerRef.current = null
      }
    }

    const handleEvent = (event: ReplayWsInbound) => {
      const store = useReplayStore.getState()

      switch (event.type) {
        case 'replay_state': {
          const hadTrail = store.trailAuthoritative
          const wasSeeking = store.phase === 'seeking'
          const sliceTrail =
            wasSeeking &&
            hadTrail &&
            !store.awaitingSnapshotReplace &&
            !store.expectImmediateTicks
          store.applyReplayState(event, { sliceTrail })
          if (store.forcePausedUntilPlay) {
            client.send({ action: 'pause' })
            store.setPhase('paused')
          }
          break
        }
        case 'snapshot':
          store.applySnapshot(event)
          if (store.forcePausedUntilPlay) {
            client.send({ action: 'pause' })
            store.setPhase('paused')
          }
          break
        case 'tick_batch':
          if (store.expectImmediateTicks) {
            store.applyTicksImmediate(event.ticks, {
              cursor: event.cursor,
              queueRemaining: event.queueRemaining,
            })
          } else {
            store.enqueueTicks(event.ticks, {
              cursor: event.cursor,
              queueRemaining: event.queueRemaining,
            })
          }
          break
        case 'buffer_loading':
          store.beginBufferLoading()
          clearBufferTimer()
          bufferTimerRef.current = window.setTimeout(() => {
            useReplayStore.getState().timeoutBufferLoading()
            bufferTimerRef.current = null
          }, REPLAY_BUFFER_UI_TIMEOUT_MS)
          break
        case 'buffer_ready': {
          clearBufferTimer()
          const readyStore = useReplayStore.getState()
          readyStore.endBufferLoading()
          if (event.latestAvailable != null) {
            const meta = useReplayStore.getState().meta
            if (meta) {
              useReplayStore.getState().applyReplayState({
                ...meta,
                latestAvailable: event.latestAvailable,
              })
            }
          }
          break
        }
        case 'buffer_reset':
          store.clearQueue()
          store.markAwaitingSnapshotReplace()
          break
        case 'replay_completed':
          store.markCompleted()
          break
        case 'error':
          if (event.code === 'SEEK_OUT_OF_RANGE') {
            showToast(event.message || 'Seek out of range')
            // Snap scrubber to last valid cursor; abort in-flight seek/oob wait
            store.cancelSeek()
          } else {
            showToast(event.message || 'Replay error')
            store.setError(event.message)
          }
          break
        default:
          break
      }
    }

    client.connect(wsUrl, {
      onOpen: () => {
        const store = useReplayStore.getState()
        store.setConnection('open')
        if (client.consumePendingPlay()) {
          store.setPhase('playing')
        }
      },
      onEvent: handleEvent,
      onClose: ({ kind }) => {
        clearBufferTimer()
        const store = useReplayStore.getState()
        store.clearExpectImmediateTicks()
        if (kind === 'unauthorized') {
          client.clearQueue()
          store.setConnection('red', 'unauthorized')
          store.setPhase('paused')
          store.setError('Authentication required')
          showToast('Session expired — sign in again')
          notifyAuthFailure('UNAUTHORIZED')
        } else if (kind === 'superseded') {
          client.clearQueue()
          store.setConnection('amber', 'superseded')
          store.setPhase('paused')
          showToast('Opened in another tab')
          onSuperseded?.()
        } else if (kind === 'not_found') {
          client.clearQueue()
          store.setConnection('amber', 'not_found')
          showToast('Replay session not found — pick a bar to start again')
          onNotFound?.()
        } else if (kind === 'error') {
          store.setConnection('red', 'error')
          if (store.phase !== 'inactive' && store.phase !== 'pick_anchor') {
            showToast('Replay connection lost')
          }
        } else {
          store.setConnection('closed')
        }
        if (clientRef.current === client) {
          clientRef.current = null
          registerWsClient(null)
        }
      },
      onError: () => {
        useReplayStore.getState().setConnection('red', 'error')
      },
    })

    return () => {
      clearBufferTimer()
      client.close()
      if (clientRef.current === client) {
        clientRef.current = null
        registerWsClient(null)
      }
    }
  }, [sessionId, wsUrl, registerWsClient, showToast, onSuperseded, onNotFound])
}
