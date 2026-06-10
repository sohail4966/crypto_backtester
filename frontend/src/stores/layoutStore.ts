import { create } from 'zustand'

export const SIDEBAR_OPEN_STORAGE_KEY = 'layout-sidebar-open'

function loadSidebarOpenPreference(): boolean {
  const stored = localStorage.getItem(SIDEBAR_OPEN_STORAGE_KEY)
  if (stored === 'false') {
    return false
  }
  return true
}

interface LayoutState {
  sidebarOpen: boolean
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void
}

export const useLayoutStore = create<LayoutState>((set) => ({
  sidebarOpen: loadSidebarOpenPreference(),
  toggleSidebar: () =>
    set((state) => {
      const next = !state.sidebarOpen
      localStorage.setItem(SIDEBAR_OPEN_STORAGE_KEY, String(next))
      return { sidebarOpen: next }
    }),
  setSidebarOpen: (open) => {
    localStorage.setItem(SIDEBAR_OPEN_STORAGE_KEY, String(open))
    set({ sidebarOpen: open })
  },
}))
