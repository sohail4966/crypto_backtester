import { useEffect, useMemo, useState } from 'react'
import { useIndicatorCatalog } from '@/hooks/useIndicatorCatalog'
import { useIndicatorStore } from '@/stores/indicatorStore'
import {
  catalogPickerLabel,
  findCatalogEntry,
  indicatorChipLabel,
  paramFieldDefs,
  primaryBundleKey,
  type ParamFieldDef,
} from '@/utils/indicatorCatalog'

interface IndicatorSettingsDialogProps {
  instanceId: string
  onClose: () => void
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

export function IndicatorSettingsDialog({ instanceId, onClose }: IndicatorSettingsDialogProps) {
  const catalogQuery = useIndicatorCatalog()
  const active = useIndicatorStore((state) => state.active)
  const updateParams = useIndicatorStore((state) => state.updateParams)

  const target = active.find((item) => item.instanceId === instanceId)
  const catalog = useMemo(() => catalogQuery.data ?? [], [catalogQuery.data])

  const catalogKey = target ? (primaryBundleKey(target.key) ?? target.key) : ''

  const entry = findCatalogEntry(catalog, catalogKey)
  const fields = entry ? paramFieldDefs(entry) : []

  const [values, setValues] = useState<Record<string, string>>({})
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!target || !entry) {
      return
    }
    const next: Record<string, string> = {}
    for (const field of paramFieldDefs(entry)) {
      const current = target.params[field.name] ?? entry.defaultParams[field.name]
      next[field.name] = current != null ? String(current) : ''
    }
    setValues(next)
    setError(null)
  }, [entry, instanceId, target])

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        onClose()
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [onClose])

  if (!target || !entry || fields.length === 0) {
    return null
  }

  const title = catalogPickerLabel(entry)

  function handleDefaults() {
    const next: Record<string, string> = {}
    for (const field of fields) {
      const value = entry!.defaultParams[field.name]
      next[field.name] = value != null ? String(value) : ''
    }
    setValues(next)
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

    const result = updateParams(instanceId, params)
    if (!result.ok) {
      setError(result.error)
      return
    }
    onClose()
  }

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 p-4"
      role="presentation"
      onMouseDown={onClose}
    >
      <div
        role="dialog"
        aria-labelledby="indicator-settings-title"
        className="w-full max-w-sm rounded-lg border border-border bg-surface shadow-xl"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="border-b border-border px-4 py-3">
          <h2 id="indicator-settings-title" className="text-sm font-semibold text-text">
            {title}
          </h2>
          <p className="mt-0.5 text-xs text-text-secondary">
            {indicatorChipLabel(target.key, target.params)}
          </p>
        </div>

        <form
          className="space-y-3 px-4 py-4"
          onSubmit={(event) => {
            event.preventDefault()
            handleApply()
          }}
        >
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
                  min={field.min}
                  step={field.step}
                  onChange={(event) =>
                    setValues((prev) => ({ ...prev, [field.name]: event.target.value }))
                  }
                  className="w-full rounded border border-border bg-bg px-2 py-1.5 text-sm text-text outline-none focus:border-accent"
                />
              )}
            </label>
          ))}

          {error ? <p className="text-xs text-bear">{error}</p> : null}

          <div className="flex items-center justify-end gap-2 pt-1">
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
      </div>
    </div>
  )
}
