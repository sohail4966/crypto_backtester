import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { VisibilityToggle } from '@/components/Icons/VisibilityToggle'
import { useTheme } from '@/hooks/useTheme'
import { useIndicatorCatalog } from '@/hooks/useIndicatorCatalog'
import { useIndicatorStore } from '@/stores/indicatorStore'
import type { ActiveIndicator } from '@/types/indicator'
import { resolveChartColor } from '@/utils/color'
import {
  bundleKeysFor,
  catalogPickerLabel,
  findCatalogEntry,
  indicatorChipLabel,
  paramFieldDefs,
  primaryBundleKey,
  type ParamFieldDef,
} from '@/utils/indicatorCatalog'
import {
  bundleSeriesStyleLabel,
  defaultBundleSeriesColor,
  INDICATOR_COLOR_PRESETS,
  INDICATOR_LINE_WIDTHS,
} from '@/utils/indicatorDisplay'

interface IndicatorSettingsDialogProps {
  onClose: () => void
}

interface SeriesStyleState {
  color: string
  lineWidth: number
  visible: boolean
}

function parseFieldValue(
  field: ParamFieldDef,
  raw: string,
): { ok: true; value: number | string } | { ok: false; message: string } {
  if (field.type === 'select') {
    if (!field.options?.includes(raw)) {
      return { ok: false, message: `Invalid ${field.label}` }
    }
    return { ok: true, value: raw }
  }

  const num = field.type === 'integer' ? parseInt(raw, 10) : parseFloat(raw)
  if (!Number.isFinite(num)) {
    return { ok: false, message: `${field.label} must be a number` }
  }
  if (field.min != null && num < field.min) {
    return { ok: false, message: `${field.label} must be >= ${field.min}` }
  }
  if (field.type === 'integer' && !Number.isInteger(num)) {
    return { ok: false, message: `${field.label} must be a whole number` }
  }
  return { ok: true, value: num }
}

function sortGroupMembers(entryKey: string, members: ActiveIndicator[]): ActiveIndicator[] {
  const order = bundleKeysFor(entryKey)
  return [...members].sort((a, b) => order.indexOf(a.key) - order.indexOf(b.key))
}

export function IndicatorSettingsDialog({ onClose }: IndicatorSettingsDialogProps) {
  const { theme } = useTheme()
  const catalogQuery = useIndicatorCatalog()
  const active = useIndicatorStore((state) => state.active)
  const settingsInstanceId = useIndicatorStore((state) => state.settingsInstanceId)
  const updateIndicatorSettings = useIndicatorStore((state) => state.updateIndicatorSettings)

  const target = settingsInstanceId
    ? active.find((item) => item.instanceId === settingsInstanceId)
    : undefined

  const catalog = useMemo(() => catalogQuery.data ?? [], [catalogQuery.data])

  const entry = useMemo(() => {
    if (!target) {
      return undefined
    }
    const catalogKey = primaryBundleKey(target.key) ?? target.key
    return findCatalogEntry(catalog, catalogKey)
  }, [catalog, target])

  const groupMembers = useMemo(() => {
    if (!target || !entry) {
      return []
    }
    return sortGroupMembers(
      entry.key,
      active.filter((item) => item.groupInstanceId === target.groupInstanceId),
    )
  }, [active, entry, target])

  const fields = entry ? paramFieldDefs(entry) : []

  const [values, setValues] = useState<Record<string, string>>({})
  const [seriesStyles, setSeriesStyles] = useState<Record<string, SeriesStyleState>>({})
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!entry || !target) {
      return
    }
    const next: Record<string, string> = {}
    for (const field of paramFieldDefs(entry)) {
      const current = target.params[field.name] ?? entry.defaultParams[field.name]
      next[field.name] = current != null ? String(current) : ''
    }
    setValues(next)

    const nextStyles: Record<string, SeriesStyleState> = {}
    for (const [lineIndex, member] of groupMembers.entries()) {
      nextStyles[member.key] = {
        color: member.color ?? defaultBundleSeriesColor(member.key, lineIndex),
        lineWidth: member.lineWidth ?? 2,
        visible: member.visible !== false,
      }
    }
    setSeriesStyles(nextStyles)
    setError(null)
  }, [entry, groupMembers, settingsInstanceId, target])

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        onClose()
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [onClose])

  if (catalogQuery.isPending) {
    return (
      <DialogShell onClose={onClose} title="Indicator settings">
        <p className="px-4 py-6 text-sm text-text-secondary">Loading catalog…</p>
      </DialogShell>
    )
  }

  if (!entry || !target || !settingsInstanceId) {
    return (
      <DialogShell onClose={onClose} title="Indicator settings">
        <p className="px-4 py-6 text-sm text-bear">Could not load indicator settings.</p>
      </DialogShell>
    )
  }

  const title = catalogPickerLabel(entry)
  const subtitle = indicatorChipLabel(target.key, target.params)

  function handleDefaults() {
    const next: Record<string, string> = {}
    for (const field of fields) {
      const value = entry!.defaultParams[field.name]
      next[field.name] = value != null ? String(value) : ''
    }
    setValues(next)

    const nextStyles: Record<string, SeriesStyleState> = {}
    for (const [lineIndex, member] of groupMembers.entries()) {
      nextStyles[member.key] = {
        color: defaultBundleSeriesColor(member.key, lineIndex),
        lineWidth: 2,
        visible: true,
      }
    }
    setSeriesStyles(nextStyles)
    setError(null)
  }

  function handleApply() {
    const params: Record<string, unknown> = {}
    for (const field of fields) {
      const parsed = parseFieldValue(field, values[field.name] ?? '')
      if (!parsed.ok) {
        setError(parsed.message)
        return
      }
      params[field.name] = parsed.value
    }

    const patch = {
      params: fields.length > 0 ? params : undefined,
      seriesStyles: Object.fromEntries(
        Object.entries(seriesStyles).map(([key, style]) => [key, { ...style }]),
      ),
    }

    const result = updateIndicatorSettings(settingsInstanceId!, patch)
    if (!result.ok) {
      setError(result.error)
      return
    }
    onClose()
  }

  const showLineVisibility = groupMembers.length > 1

  return (
    <DialogShell onClose={onClose} title={title} subtitle={subtitle} wide={groupMembers.length > 1}>
      <form
        className="flex min-h-0 flex-1 flex-col"
        onSubmit={(event) => {
          event.preventDefault()
          handleApply()
        }}
      >
        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-4">
        {fields.length > 0 ? (
          <div className="space-y-3">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-text-secondary">
              Inputs
            </p>
            {fields.map((field) => (
              <label key={field.name} className="block text-xs">
                <span className="mb-1 block text-text-secondary">{field.label}</span>
                {field.type === 'select' ? (
                  <select
                    value={values[field.name] ?? ''}
                    onChange={(event) =>
                      setValues((prev) => ({ ...prev, [field.name]: event.target.value }))
                    }
                    className="w-full rounded border border-border bg-bg px-2 py-1.5 text-sm text-text outline-none focus:border-accent"
                  >
                    {(field.options ?? []).map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="number"
                    value={values[field.name] ?? ''}
                    min={field.type === 'integer' ? field.min : undefined}
                    step={field.type === 'float' ? 'any' : field.step}
                    onChange={(event) =>
                      setValues((prev) => ({ ...prev, [field.name]: event.target.value }))
                    }
                    className="w-full rounded border border-border bg-bg px-2 py-1.5 text-sm text-text outline-none focus:border-accent"
                  />
                )}
              </label>
            ))}
          </div>
        ) : null}

        <div className="space-y-3">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-text-secondary">
            Style
          </p>
          {groupMembers.map((member) => (
            <SeriesStyleEditor
              key={member.key}
              label={bundleSeriesStyleLabel(member.key)}
              style={seriesStyles[member.key] ?? {
                color: defaultBundleSeriesColor(member.key, 0),
                lineWidth: 2,
                visible: true,
              }}
              theme={theme}
              showVisibility={showLineVisibility}
              onChange={(next) =>
                setSeriesStyles((prev) => ({
                  ...prev,
                  [member.key]: next,
                }))
              }
            />
          ))}
        </div>

        {error ? <p className="text-xs text-bear">{error}</p> : null}
        </div>

        <div className="flex shrink-0 items-center justify-end gap-2 border-t border-border px-4 py-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded border border-border px-3 py-1.5 text-xs text-text-secondary hover:text-text"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleDefaults}
            className="rounded border border-border px-3 py-1.5 text-xs text-text-secondary hover:text-text"
          >
            Defaults
          </button>
          <button
            type="submit"
            className="rounded border border-accent bg-accent/10 px-3 py-1.5 text-xs font-medium text-accent hover:bg-accent/20"
          >
            OK
          </button>
        </div>
      </form>
    </DialogShell>
  )
}

function SeriesStyleEditor({
  label,
  style,
  theme,
  showVisibility,
  onChange,
}: {
  label: string
  style: SeriesStyleState
  theme: ReturnType<typeof useTheme>['theme']
  showVisibility: boolean
  onChange: (next: SeriesStyleState) => void
}) {
  const previewColor = resolveChartColor(style.color, theme)

  return (
    <div
      className={`rounded border border-border bg-bg/40 p-3 ${
        showVisibility && !style.visible ? 'opacity-60' : ''
      }`}
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <p
          className={`text-xs font-medium ${
            showVisibility && !style.visible ? 'text-text/50 line-through' : 'text-text'
          }`}
        >
          {label}
        </p>
        {showVisibility ? (
          <VisibilityToggle
            visible={style.visible}
            label={label}
            onToggle={() => onChange({ ...style, visible: !style.visible })}
            className="shrink-0 rounded p-0.5 text-text-secondary transition-colors hover:bg-bg hover:text-text"
          />
        ) : null}
      </div>
      <div className="flex flex-wrap gap-2">
        {INDICATOR_COLOR_PRESETS.map((preset) => {
          const swatch = resolveChartColor(preset.value, theme)
          const selected = style.color === preset.value
          return (
            <button
              key={preset.value}
              type="button"
              title={preset.label}
              aria-label={`${label} ${preset.label}`}
              onClick={() => onChange({ ...style, color: preset.value })}
              className={`h-6 w-6 rounded-full border-2 transition-transform hover:scale-105 ${
                selected ? 'border-text ring-2 ring-accent/40' : 'border-border'
              }`}
              style={{ backgroundColor: swatch }}
            />
          )
        })}
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 text-xs text-text-secondary">
          <span>Custom</span>
          <input
            type="color"
            value={previewColor}
            onChange={(event) => onChange({ ...style, color: event.target.value })}
            className="h-7 w-9 cursor-pointer rounded border border-border bg-bg"
          />
        </label>
        <div className="flex items-center gap-2">
          <span className="text-xs text-text-secondary">Width</span>
          <div className="flex gap-1">
            {INDICATOR_LINE_WIDTHS.map((width) => (
              <button
                key={width}
                type="button"
                onClick={() => onChange({ ...style, lineWidth: width })}
                className={`rounded border px-2 py-0.5 text-xs ${
                  style.lineWidth === width
                    ? 'border-accent bg-accent/10 text-accent'
                    : 'border-border text-text-secondary hover:text-text'
                }`}
              >
                {width}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function DialogShell({
  children,
  onClose,
  title,
  subtitle,
  wide = false,
}: {
  children: ReactNode
  onClose: () => void
  title: string
  subtitle?: string
  wide?: boolean
}) {
  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 p-4"
      role="presentation"
      onMouseDown={onClose}
    >
      <div
        role="dialog"
        aria-labelledby="indicator-settings-title"
        className={`flex max-h-[min(90vh,calc(100dvh-2rem))] w-full flex-col overflow-hidden rounded-lg border border-border bg-surface shadow-xl ${
          wide ? 'max-w-md' : 'max-w-sm'
        }`}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="shrink-0 border-b border-border px-4 py-3">
          <h2 id="indicator-settings-title" className="text-sm font-semibold text-text">
            {title}
          </h2>
          {subtitle ? (
            <p className="mt-0.5 text-xs text-text-secondary">{subtitle}</p>
          ) : null}
        </div>
        <div className="flex min-h-0 flex-1 flex-col">{children}</div>
      </div>
    </div>
  )
}
