import type { ActiveIndicator, IndicatorSpec } from '@/types/indicator'

/** Visible+pane+deduped specs — same rules as ChartContainer / create payload. */
export function visibleIndicatorSpecs(
  active: ActiveIndicator[],
): IndicatorSpec[] {
  const seen = new Set<string>()
  const specs: IndicatorSpec[] = []
  for (const item of active) {
    if (item.visible === false) {
      continue
    }
    const id = `${item.key}:${JSON.stringify(item.params)}:${item.pane}`
    if (seen.has(id)) {
      continue
    }
    seen.add(id)
    specs.push({ key: item.key, params: item.params, pane: item.pane })
  }
  return specs
}

export function specsFingerprint(specs: IndicatorSpec[]): string {
  return JSON.stringify(
    specs.map((s) => ({
      key: s.key,
      params: s.params,
      pane: s.pane ?? null,
    })),
  )
}
