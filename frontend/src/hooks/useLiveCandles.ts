import { useEffect, useRef } from 'react'
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
  const onCandleRef = useRef(onCandle)
  onCandleRef.current = onCandle

  useEffect(() => {
    if (!isLiveWsEnabled() || !enabled || !symbolId) {
      return
    }

    const client = new LiveWsClient()
    client.connect({
      onCandle: (payload) => {
        if (payload.incomplete) {
          return
        }
        if (payload.symbol !== symbolId || payload.timeframe !== timeframe) {
          return
        }
        onCandleRef.current(payload.candle)
      },
    })
    client.subscribe(symbolId, timeframe)

    return () => {
      client.unsubscribe(symbolId, timeframe)
      client.close()
    }
  }, [enabled, symbolId, timeframe])
}
