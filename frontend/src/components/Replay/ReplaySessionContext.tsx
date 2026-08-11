import { createContext, useContext, type ReactNode } from 'react'
import type { ReplaySessionApi } from '@/hooks/useReplaySession'

const ReplaySessionContext = createContext<ReplaySessionApi | null>(null)

export function ReplaySessionProvider({
  value,
  children,
}: {
  value: ReplaySessionApi
  children: ReactNode
}) {
  return (
    <ReplaySessionContext.Provider value={value}>
      {children}
    </ReplaySessionContext.Provider>
  )
}

export function useReplaySessionContext(): ReplaySessionApi {
  const ctx = useContext(ReplaySessionContext)
  if (!ctx) {
    throw new Error('useReplaySessionContext must be used within ReplaySessionProvider')
  }
  return ctx
}

export function useOptionalReplaySession(): ReplaySessionApi | null {
  return useContext(ReplaySessionContext)
}
