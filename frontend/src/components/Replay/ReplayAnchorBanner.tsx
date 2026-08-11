export function ReplayAnchorBanner() {
  return (
    <div
      role="status"
      className="pointer-events-none absolute inset-x-0 top-3 z-20 flex justify-center"
    >
      <div className="rounded border border-accent/40 bg-surface/95 px-4 py-2 text-sm text-text shadow-md">
        Click a bar to start replay
      </div>
    </div>
  )
}
