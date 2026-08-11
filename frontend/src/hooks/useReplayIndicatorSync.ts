import { useEffect, useRef } from 'react'
import { useOptionalReplaySession } from '@/components/Replay/ReplaySessionContext'
import { useIndicatorStore } from '@/stores/indicatorStore'
import { useReplayStore } from '@/stores/replayStore'
import {
  specsFingerprint,
  visibleIndicatorSpecs,
} from '@/utils/replayIndicators'

/** Mid-session visible-indicator changes → set_indicators + force pause. */
export function useReplayIndicatorSync(): void {
  const session = useOptionalReplaySession()
  const active = useIndicatorStore((s) => s.active)
  const trailAuthoritative = useReplayStore((s) => s.trailAuthoritative)
  const sessionId = useReplayStore((s) => s.sessionId)
  const fingerprint = specsFingerprint(visibleIndicatorSpecs(active))
  const prevRef = useRef<string | null>(null)
  const readyRef = useRef(false)

  useEffect(() => {
    if (!trailAuthoritative || !sessionId || sessionId === 'pending') {
      prevRef.current = fingerprint
      readyRef.current = false
      return
    }

    // Skip the first fingerprint after trail becomes authoritative (create payload already sent)
    if (!readyRef.current) {
      prevRef.current = fingerprint
      readyRef.current = true
      return
    }

    if (prevRef.current === fingerprint) {
      return
    }
    prevRef.current = fingerprint
    session?.sendSetIndicators()
  }, [fingerprint, trailAuthoritative, sessionId, session])
}
