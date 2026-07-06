interface ReplayAnchorBannerProps {
  onCancel: () => void
}

export function ReplayAnchorBanner({ onCancel }: ReplayAnchorBannerProps) {
  return (
    <div className="pointer-events-auto absolute inset-x-0 top-3 z-20 flex justify-center px-4">
      <div className="flex items-center gap-3 rounded-lg border border-accent/30 bg-surface/95 px-4 py-2 text-sm shadow-lg backdrop-blur">
        <span className="text-text">Click a bar to set the replay start point</span>
        <button
          type="button"
          onClick={onCancel}
          className="rounded px-2 py-0.5 text-xs text-text-secondary transition-colors hover:bg-bg hover:text-text"
        >
          Cancel
        </button>
        <span className="text-xs text-text-secondary">Esc</span>
      </div>
    </div>
  )
}
