import { useEffect, useRef } from 'react'
import { useToast } from '@/components/ui/Toast'
import { notifyAuthFailure } from '@/services/authSession'
import { isLiveWsEnabled, LiveWsClient } from '@/services/liveWsClient'
import type { OHLCVBar } from '@/types/candle'

/**
 * Subscribe the active pane to /ws/live and upsert bars into the assembled series
 * via the provided callback (FE-005 hybrid A+C — active subscription only).
 */
export function useLiveCandles(
  symbolId: string | undefined,
  timeframe: string,
  enabled: boolean,
  onCandle: (bar: OHLCVBar) => void,
): void {
  const { showToast } = useToast()
  const onCandleRef = useRef(onCandle)
  onCandleRef.current = onCandle

  useEffect(() => {
    if (!isLiveWsEnabled() || !enabled || !symbolId) {
      return
    }

    const client = new LiveWsClient()
    let cancelled = false

    void client
      .connect({
        onCandle: (payload) => {
          if (payload.symbol !== symbolId || payload.timeframe !== timeframe) {
            return
          }
          onCandleRef.current(payload.bar)
        },
        onClose: ({ kind }) => {
          if (kind === 'unauthorized') {
            notifyAuthFailure('UNAUTHORIZED')
            showToast('Session expired — sign in again')
          } else if (kind === 'rate_limited') {
            showToast('Too many concurrent WebSocket connections')
          }
        },
      })
      .then(() => {
        if (cancelled) {
          client.close()
          return
        }
        client.subscribe(symbolId, timeframe)
      })
      .catch(() => {
        // Ticket mint / connect failed — leave live WS silent, REST fallback covers.
      })

    return () => {
      cancelled = true
      client.unsubscribe(symbolId, timeframe)
      client.close()
    }
  }, [enabled, symbolId, timeframe, showToast])
}
