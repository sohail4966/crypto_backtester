import { useLocation } from 'react-router-dom'
import { ReplaySessionProvider } from '@/components/Replay/ReplaySessionContext'
import { useReplayIndicatorSync } from '@/hooks/useReplayIndicatorSync'
import { useReplayKeyboard } from '@/hooks/useReplayKeyboard'
import { useReplaySession } from '@/hooks/useReplaySession'
import { useReplayTick } from '@/hooks/useReplayTick'
import { useReplayWs } from '@/hooks/useReplayWs'
import { useReplayStore } from '@/stores/replayStore'
import type { ReactNode } from 'react'

function ReplayHooks({ children }: { children: ReactNode }) {
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

/** Provides replay session API + hooks for chart route (topbar toggle + chart page). */
export function ReplayRoot({ children }: { children: ReactNode }) {
  const location = useLocation()
  if (location.pathname !== '/') {
    return <>{children}</>
  }
  return <ReplayHooks>{children}</ReplayHooks>
}
