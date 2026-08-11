import { MultiChartLayout } from '@/components/Layout/MultiChartLayout'
import { IndicatorSettingsDialog } from '@/components/Indicators/IndicatorSettingsDialog'
import { ReplayAnchorBanner } from '@/components/Replay/ReplayAnchorBanner'
import { ReplayBottomBar } from '@/components/Replay/ReplayBottomBar'
import { useOptionalReplaySession } from '@/components/Replay/ReplaySessionContext'
import { useDefaultSymbol } from '@/hooks/useDefaultSymbol'
import { useIndicatorStore } from '@/stores/indicatorStore'
import { sessionActivePhase, useReplayStore } from '@/stores/replayStore'

export function ChartPage() {
  useDefaultSymbol()
  const settingsInstanceId = useIndicatorStore((state) => state.settingsInstanceId)
  const closeSettings = useIndicatorStore((state) => state.closeSettings)
  const phase = useReplayStore((s) => s.phase)
  const session = useOptionalReplaySession()

  const showBanner = phase === 'pick_anchor'
  const showBottomBar = sessionActivePhase(phase)

  return (
    <div className="-m-6 flex h-full min-h-0 flex-1 flex-col">
      <div className="relative min-h-0 flex-1">
        <MultiChartLayout />
        {showBanner ? <ReplayAnchorBanner /> : null}
      </div>

      {showBottomBar && session ? (
        <ReplayBottomBar
          onPlay={session.play}
          onPause={session.pause}
          onStop={() => {
            void session.stopToPickAnchor()
          }}
          onStep={session.step}
          onSeek={session.seek}
          onSpeedChange={session.setSpeed}
        />
      ) : null}

      {settingsInstanceId ? (
        <IndicatorSettingsDialog onClose={closeSettings} />
      ) : null}
    </div>
  )
}
