import { create } from 'zustand'
import type { Drawing, DrawingDraft, DrawingType } from '@/types/drawing'

interface DrawingState {
  drawings: Drawing[]
  activeTool: DrawingType | null
  selectedId: string | null
  draft: DrawingDraft
  hydrated: boolean

  hydrate: (drawings: Drawing[]) => void
  setActiveTool: (tool: DrawingType | null) => void
  clearTool: () => void
  setDraft: (draft: DrawingDraft) => void
  clearDraft: () => void
  setSelectedId: (id: string | null) => void
  addDrawing: (drawing: Drawing) => void
  updateDrawing: (id: string, patch: Partial<Drawing>) => void
  removeDrawing: (id: string) => void
  removeSelected: () => void
  /** True when Esc should be consumed by drawings before replay. */
  consumesEscape: () => boolean
  handleEscape: () => boolean
}

function newId(): string {
  return crypto.randomUUID()
}

export function createDrawingId(): string {
  return newId()
}

export const useDrawingStore = create<DrawingState>((set, get) => ({
  drawings: [],
  activeTool: null,
  selectedId: null,
  draft: null,
  hydrated: false,

  hydrate: (drawings) =>
    set({
      drawings: [...drawings],
      hydrated: true,
      activeTool: null,
      selectedId: null,
      draft: null,
    }),

  setActiveTool: (tool) =>
    set({
      activeTool: tool,
      draft: null,
      selectedId: null,
    }),

  clearTool: () => set({ activeTool: null, draft: null }),

  setDraft: (draft) => set({ draft }),

  clearDraft: () => set({ draft: null }),

  setSelectedId: (id) => set({ selectedId: id }),

  addDrawing: (drawing) =>
    set((state) => ({
      drawings: [...state.drawings, drawing],
      activeTool: null,
      draft: null,
      selectedId: drawing.id,
    })),

  updateDrawing: (id, patch) =>
    set((state) => ({
      drawings: state.drawings.map((d) =>
        d.id === id ? ({ ...d, ...patch, id: d.id, type: d.type } as Drawing) : d,
      ),
    })),

  removeDrawing: (id) =>
    set((state) => ({
      drawings: state.drawings.filter((d) => d.id !== id),
      selectedId: state.selectedId === id ? null : state.selectedId,
    })),

  removeSelected: () => {
    const id = get().selectedId
    if (id) {
      get().removeDrawing(id)
    }
  },

  consumesEscape: () => {
    const { draft, activeTool, selectedId } = get()
    return draft != null || activeTool != null || selectedId != null
  },

  handleEscape: () => {
    const { draft, activeTool, selectedId } = get()
    if (draft != null) {
      set({ draft: null })
      return true
    }
    if (activeTool != null) {
      set({ activeTool: null, draft: null })
      return true
    }
    if (selectedId != null) {
      set({ selectedId: null })
      return true
    }
    return false
  },
}))

export function drawingsFor(
  drawings: Drawing[],
  symbolId: string,
  timeframe: string,
): Drawing[] {
  return drawings.filter(
    (d) => d.symbolId === symbolId && d.timeframe === timeframe && d.visible,
  )
}
