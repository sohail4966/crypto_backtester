import { act, fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ReplayBottomBar } from '@/components/Replay/ReplayBottomBar'
import { ReplayScrubber } from '@/components/Replay/ReplayScrubber'
import { ReplayAnchorBanner } from '@/components/Replay/ReplayAnchorBanner'
import { useReplayStore } from '@/stores/replayStore'

describe('ReplayBottomBar', () => {
  beforeEach(() => {
    useReplayStore.getState().reset()
    useReplayStore.getState().beginConnect('s1', '/ws/replay/s1')
    useReplayStore.getState().applyReplayState({
      sessionId: 's1',
      symbol: 'BTC/USDT',
      timeframe: '1h',
      stepTimeframe: '1h',
      startAnchor: 100,
      latestAvailable: 500,
      cursor: 200,
      serverState: 'paused',
      speed: 1,
      barIndex: 1,
      queueRemaining: 50,
      indicators: [],
    })
    useReplayStore.getState().setPhase('paused')
    useReplayStore.getState().setConnection('open')
  })

  it('fires play/pause/stop/step/speed callbacks', () => {
    const onPlay = vi.fn()
    const onPause = vi.fn()
    const onStop = vi.fn()
    const onStep = vi.fn()
    const onSeek = vi.fn()
    const onSpeedChange = vi.fn()

    const { rerender } = render(
      <ReplayBottomBar
        onPlay={onPlay}
        onPause={onPause}
        onStop={onStop}
        onStep={onStep}
        onSeek={onSeek}
        onSpeedChange={onSpeedChange}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Play' }))
    expect(onPlay).toHaveBeenCalled()

    act(() => {
      useReplayStore.getState().setPhase('playing')
    })
    rerender(
      <ReplayBottomBar
        onPlay={onPlay}
        onPause={onPause}
        onStop={onStop}
        onStep={onStep}
        onSeek={onSeek}
        onSpeedChange={onSpeedChange}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Pause' }))
    expect(onPause).toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: 'Step forward' }))
    expect(onStep).toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: 'Stop' }))
    expect(onStop).toHaveBeenCalled()

    fireEvent.change(screen.getByLabelText('Replay speed'), {
      target: { value: '2' },
    })
    expect(onSpeedChange).toHaveBeenCalledWith(2)
  })
})

describe('ReplayScrubber', () => {
  it('computes progress and disables when denom invalid', () => {
    const { rerender } = render(
      <ReplayScrubber
        startAnchor={100}
        cursor={300}
        latestAvailable={500}
        completed={false}
        onSeek={vi.fn()}
      />,
    )
    const slider = screen.getByRole('slider', { name: 'Replay position' })
    expect(slider).toHaveAttribute('aria-valuenow', '50')
    expect(slider.getAttribute('title') ?? '').toMatch(/latestAvailable/)

    rerender(
      <ReplayScrubber
        startAnchor={100}
        cursor={100}
        latestAvailable={null}
        completed={false}
        onSeek={vi.fn()}
      />,
    )
    expect(screen.getByRole('slider')).toHaveAttribute('aria-valuenow', '0')
    expect(screen.getByRole('slider')).toHaveAttribute('aria-disabled', 'true')

    rerender(
      <ReplayScrubber
        startAnchor={100}
        cursor={500}
        latestAvailable={500}
        completed
        onSeek={vi.fn()}
      />,
    )
    expect(screen.getByRole('slider')).toHaveAttribute('aria-valuenow', '100')
  })
})

describe('ReplayAnchorBanner', () => {
  it('renders pick-anchor message', () => {
    render(<ReplayAnchorBanner />)
    expect(screen.getByText('Click a bar to start replay')).toBeInTheDocument()
  })
})
