import { useCallback, useEffect } from 'react'
import { ChartContainer } from '@/components/Chart/ChartContainer'
import { IndicatorSettingsDialog } from '@/components/Indicators/IndicatorSettingsDialog'
import { ReplayAnchorBanner } from '@/components/Replay/ReplayAnchorBanner'
import { ReplayBottomBar } from '@/components/Replay/ReplayBottomBar'
import { useDefaultSymbol } from '@/hooks/useDefaultSymbol'
import { useReplaySession } from '@/hooks/useReplaySession'
import { useReplayTick } from '@/hooks/useReplayTick'
import { useChartStore } from '@/stores/chartStore'
import { useIndicatorStore } from '@/stores/indicatorStore'
import { useReplayStore } from '@/stores/replayStore'

export function ChartPage() {
  useDefaultSymbol()
  const settingsInstanceId = useIndicatorStore((state) => state.settingsInstanceId)
  const closeSettings = useIndicatorStore((state) => state.closeSettings)
  const replayMode = useChartStore((state) => state.replayMode)
  const setReplayMode = useChartStore((state) => state.setReplayMode)
  const phase = useReplayStore((state) => state.phase)
  const sessionId = useReplayStore((state) => state.sessionId)
  const speed = useReplayStore((state) => state.speed)

  const { startSessionAt, stopSession, sendCommand } = useReplaySession()

  const replayChartSession =
    sessionId != null &&
    phase !== 'inactive' &&
    phase !== 'pick_anchor' &&
    phase !== 'error'

  const replayControlsVisible = replayChartSession && phase !== 'connecting'

  const sendPlay = useCallback(() => {
    sendCommand({ action: 'play', speed })
    useReplayStore.getState().playLocally()
  }, [sendCommand, speed])

  const sendPause = useCallback(() => {
    sendCommand({ action: 'pause' })
    useReplayStore.getState().pauseLocally()
  }, [sendCommand])

  const sendRefill = useCallback(() => {
    sendCommand({ action: 'refill' })
  }, [sendCommand])

  useReplayTick({
    sendRefill,
    onCursorAdvanced: () => {
      // followReplay viewport scroll can be added when chart exposes scroll API
    },
  })

  const handlePlay = () => {
    const state = useReplayStore.getState()
    if (
      state.phase === 'ready' ||
      state.phase === 'paused' ||
      (state.phase === 'playing' && state.tickQueue.length === 0)
    ) {
      sendPlay()
    }
  }

  const handlePause = () => {
    sendPause()
  }

  const handleStop = () => {
    void stopSession()
  }

  const handleStep = () => {
    sendCommand({ action: 'step', count: 1 })
  }

  const handleSeek = (to: number) => {
    sendCommand({ action: 'seek', to })
  }

  const handleSetSpeed = (nextSpeed: number) => {
    useReplayStore.getState().setSpeed(nextSpeed)
    sendCommand({ action: 'set_speed', speed: nextSpeed })
  }

  useEffect(() => {
    if (!replayControlsVisible) {
      return
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== ' ' || event.target instanceof HTMLInputElement) {
        return
      }
      event.preventDefault()
      const phaseNow = useReplayStore.getState().phase
      if (phaseNow === 'playing') {
        sendCommand({ action: 'pause' })
        useReplayStore.getState().pauseLocally()
      } else if (phaseNow === 'ready' || phaseNow === 'paused') {
        sendCommand({ action: 'play', speed: useReplayStore.getState().speed })
        useReplayStore.getState().playLocally()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [replayControlsVisible, sendCommand])

  return (
    <div className="-m-6 flex h-full min-h-0 flex-1 flex-col">
      <div className="relative min-h-0 flex-1">
        <ChartContainer
          className="relative h-full min-h-0 flex-1"
          pickAnchorMode={replayMode && phase === 'pick_anchor'}
          replaySessionActive={replayChartSession}
          onPickAnchor={(time, baseline) => {
            void startSessionAt(time, baseline)
          }}
        />
        {replayMode && phase === 'pick_anchor' ? (
          <ReplayAnchorBanner
            onCancel={() => {
              useReplayStore.getState().setInactive()
              setReplayMode(false)
            }}
          />
        ) : null}
      </div>

      {replayControlsVisible ? (
        <ReplayBottomBar
          onPlay={handlePlay}
          onPause={handlePause}
          onStop={handleStop}
          onStep={handleStep}
          onSeek={handleSeek}
          onSetSpeed={handleSetSpeed}
        />
      ) : null}

      {settingsInstanceId ? <IndicatorSettingsDialog onClose={closeSettings} /> : null}
    </div>
  )
}
