import { VisibilityToggle } from '@/components/Icons/VisibilityToggle'

function SettingsIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-3.5 w-3.5 shrink-0"
      aria-hidden
    >
      <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l-.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  )
}

export interface IndicatorTabProps {
  label: string
  value?: string
  color?: string
  visible: boolean
  hasSettings?: boolean
  onToggleVisible: () => void
  onOpenSettings?: () => void
  onRemove?: () => void
  compact?: boolean
}

export function IndicatorTab({
  label,
  value,
  color,
  visible,
  hasSettings = false,
  onToggleVisible,
  onOpenSettings,
  onRemove,
  compact = false,
}: IndicatorTabProps) {
  return (
    <div
      className={`inline-flex shrink-0 items-center gap-1 rounded border border-border bg-surface/90 text-xs backdrop-blur-sm ${
        compact ? 'px-1.5 py-0.5' : 'px-2 py-1'
      } ${visible ? '' : 'opacity-60'}`}
    >
      {color ? (
        <span
          className="h-2 w-2 shrink-0 rounded-full"
          style={{ backgroundColor: color }}
          aria-hidden
        />
      ) : null}
      <span
        className={`whitespace-nowrap font-medium ${visible ? 'text-text' : 'text-text/50 line-through'}`}
      >
        {label}
      </span>
      {value != null && visible ? (
        <span className="whitespace-nowrap text-text-secondary">{value}</span>
      ) : null}
      <VisibilityToggle
        visible={visible}
        label={label}
        onToggle={onToggleVisible}
        className="shrink-0 rounded p-0.5 text-text-secondary transition-colors hover:bg-bg hover:text-text"
      />
      {hasSettings && onOpenSettings ? (
        <button
          type="button"
          aria-label={`Settings for ${label}`}
          onClick={onOpenSettings}
          className="shrink-0 rounded p-0.5 text-text-secondary transition-colors hover:bg-bg hover:text-accent"
        >
          <SettingsIcon />
        </button>
      ) : null}
      {onRemove ? (
        <button
          type="button"
          aria-label={`Remove ${label}`}
          onClick={onRemove}
          className="shrink-0 rounded p-0.5 text-[11px] leading-none text-text-secondary transition-colors hover:bg-bg hover:text-bear"
        >
          ×
        </button>
      ) : null}
    </div>
  )
}
