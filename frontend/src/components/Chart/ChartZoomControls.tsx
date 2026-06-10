import { useCallback, useEffect, useRef, useState } from 'react'
import { useChartContext } from '@/components/Chart/ChartContext'
import { ZOOM_CONTROLS_AUTO_HIDE_MS } from '@/constants/chart'
import { useTheme } from '@/hooks/useTheme'
import { useChartZoom } from '@/hooks/useChartZoom'
import { useChartStore } from '@/stores/chartStore'

interface ChartZoomControlsProps {
  barCount: number
}

function ResetIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-4 w-4"
      aria-hidden
    >
      <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" />
      <path d="M21 3v5h-5" />
      <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" />
      <path d="M3 21v-5h5" />
    </svg>
  )
}

export function ChartZoomControls({ barCount }: ChartZoomControlsProps) {
  const { chart } = useChartContext()
  const { zoomIn, zoomOut, resetZoom } = useChartZoom(chart, barCount)
  const { theme } = useTheme()
  const zoomControlsPulse = useChartStore((state) => state.zoomControlsPulse)
  const pulseZoomControls = useChartStore((state) => state.pulseZoomControls)

  const [visible, setVisible] = useState(false)
  const hoveringRef = useRef(false)
  const hideTimerRef = useRef<number | null>(null)

  const clearHideTimer = useCallback(() => {
    if (hideTimerRef.current != null) {
      window.clearTimeout(hideTimerRef.current)
      hideTimerRef.current = null
    }
  }, [])

  const scheduleHide = useCallback(
    (delayMs: number) => {
      clearHideTimer()
      hideTimerRef.current = window.setTimeout(() => {
        if (!hoveringRef.current) {
          setVisible(false)
        }
      }, delayMs)
    },
    [clearHideTimer],
  )

  const revealControls = useCallback(
    (autoHideMs = ZOOM_CONTROLS_AUTO_HIDE_MS) => {
      setVisible(true)
      if (!hoveringRef.current) {
        scheduleHide(autoHideMs)
      }
    },
    [scheduleHide],
  )

  useEffect(() => {
    if (zoomControlsPulse > 0) {
      revealControls()
    }
  }, [revealControls, zoomControlsPulse])

  useEffect(() => () => clearHideTimer(), [clearHideTimer])

  const onEnterZone = () => {
    hoveringRef.current = true
    clearHideTimer()
    setVisible(true)
  }

  const onLeaveZone = () => {
    hoveringRef.current = false
    scheduleHide(400)
  }

  const handleZoomOut = () => {
    zoomOut()
    pulseZoomControls()
  }

  const handleZoomIn = () => {
    zoomIn()
    pulseZoomControls()
  }

  const handleReset = () => {
    resetZoom()
    pulseZoomControls()
  }

  const barClass =
    theme === 'dark'
      ? 'border-white/30 bg-[#2a2e39]/95 text-white shadow-lg shadow-black/40'
      : 'border-gray-300 bg-white/95 text-gray-900 shadow-lg shadow-black/10'
  const buttonClass =
    theme === 'dark'
      ? 'text-white/90 hover:bg-white/15 hover:text-white'
      : 'text-gray-800 hover:bg-gray-100 hover:text-gray-950'
  const dividerClass = theme === 'dark' ? 'bg-white/25' : 'bg-gray-300'

  return (
    <div
      className="pointer-events-auto absolute bottom-[5.5rem] left-1/2 z-30 flex h-16 w-56 -translate-x-1/2 items-end justify-center pb-1"
      onMouseEnter={onEnterZone}
      onMouseLeave={onLeaveZone}
    >
      <div
        className={[
          'flex items-center overflow-hidden rounded-lg border backdrop-blur-md transition-all duration-300',
          barClass,
          visible ? 'translate-y-0 opacity-100' : 'pointer-events-none translate-y-2 opacity-0',
        ].join(' ')}
        aria-hidden={!visible}
      >
        <button
          type="button"
          aria-label="Zoom out"
          onClick={handleZoomOut}
          tabIndex={visible ? 0 : -1}
          className={`flex h-9 w-10 items-center justify-center transition-colors ${buttonClass}`}
        >
          <span className="text-lg font-medium leading-none">−</span>
        </button>
        <div className={`h-6 w-px ${dividerClass}`} aria-hidden />
        <button
          type="button"
          aria-label="Zoom in"
          onClick={handleZoomIn}
          tabIndex={visible ? 0 : -1}
          className={`flex h-9 w-10 items-center justify-center transition-colors ${buttonClass}`}
        >
          <span className="text-lg font-medium leading-none">+</span>
        </button>
        <div className={`h-6 w-px ${dividerClass}`} aria-hidden />
        <button
          type="button"
          aria-label="Reset zoom"
          onClick={handleReset}
          tabIndex={visible ? 0 : -1}
          className={`flex h-9 w-10 items-center justify-center transition-colors ${buttonClass}`}
        >
          <ResetIcon />
        </button>
      </div>
    </div>
  )
}
