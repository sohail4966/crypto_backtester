import { ReplaySessionProvider } from '@/components/Replay/ReplaySessionContext'
import { useReplayIndicatorSync } from '@/hooks/useReplayIndicatorSync'
import { useReplayKeyboard } from '@/hooks/useReplayKeyboard'
import { useReplaySession } from '@/hooks/useReplaySession'
import { useReplayTick } from '@/hooks/useReplayTick'
import { useReplayWs } from '@/hooks/useReplayWs'
import { useReplayStore } from '@/stores/replayStore'
import type { ReactNode } from 'react'

/**
 * Always-mounted replay session + WS (FE-008). Chart chrome stays route-aware
 * elsewhere; navigating to /backtest no longer tears down the socket.
 */
export function ReplayRoot({ children }: { children: ReactNode }) {
  const session = useReplaySession()

  useReplayWs({
    registerWsClient: session.registerWsClient,
    onNotFound: () => {
      void session.stopToPickAnchor().then(() => {
        // Preserve amber after teardown so AC-9 connection state remains visible
        useReplayStore.getState().setConnection('amber', 'not_found')
      })
    },
  })
  useReplayTick({ getWsClient: session.getWsClient })
  useReplayKeyboard({
    play: session.play,
    pause: session.pause,
    step: session.step,
  })
  useReplayIndicatorSync()

  return (
    <ReplaySessionProvider value={session}>{children}</ReplaySessionProvider>
  )
}
