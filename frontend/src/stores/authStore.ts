import { create } from 'zustand'

export type AuthSessionStatus =
  | 'unknown'
  | 'authenticated'
  | 'needs_auth'
  | 'expired'

interface AuthState {
  session: AuthSessionStatus
  userId: string | null
  email: string | null
  name: string | null
  lastErrorCode: string | null
  setAuthenticated: (user: {
    userId: string
    email: string
    name: string
  }) => void
  setNeedsAuth: () => void
  markExpired: (code?: string | null) => void
  clear: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  session: 'unknown',
  userId: null,
  email: null,
  name: null,
  lastErrorCode: null,

  setAuthenticated: (user) =>
    set({
      session: 'authenticated',
      userId: user.userId,
      email: user.email,
      name: user.name,
      lastErrorCode: null,
    }),

  setNeedsAuth: () =>
    set({
      session: 'needs_auth',
      userId: null,
      email: null,
      name: null,
      lastErrorCode: null,
    }),

  markExpired: (code = null) =>
    set({
      session: 'expired',
      userId: null,
      email: null,
      name: null,
      lastErrorCode: code,
    }),

  clear: () =>
    set({
      session: 'unknown',
      userId: null,
      email: null,
      name: null,
      lastErrorCode: null,
    }),
}))
