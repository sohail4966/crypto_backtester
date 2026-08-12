import { create } from 'zustand'

interface AuthState {
  userId: string | null
  email: string | null
  name: string | null
  setUser: (user: { userId: string; email: string; name: string }) => void
  clear: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  userId: null,
  email: null,
  name: null,

  setUser: (user) =>
    set({
      userId: user.userId,
      email: user.email,
      name: user.name,
    }),

  clear: () =>
    set({
      userId: null,
      email: null,
      name: null,
    }),
}))
