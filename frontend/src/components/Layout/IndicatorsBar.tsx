/** Phase 2 entry point — indicator picker and active list will mount here. */
export function IndicatorsBar() {
  return (
    <div className="flex min-w-0 flex-1 items-center gap-3 border-l border-border pl-4">
      <span className="shrink-0 text-xs font-semibold uppercase tracking-wider text-text-secondary">
        Indicators
      </span>
      <button
        type="button"
        disabled
        title="Indicator library arrives in Phase 2"
        className="rounded border border-dashed border-border px-2.5 py-1 text-xs text-text-secondary opacity-60"
      >
        + Add indicator
      </button>
    </div>
  )
}
