import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { App } from './App'

describe('App', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          status: 'ok',
          version: '0.4.1',
          database: 'ok',
        }),
      }),
    )
  })

  it('renders the chart route inside the app shell', async () => {
    window.history.pushState({}, '', '/')
    render(<App />)

    expect(screen.getByRole('heading', { name: 'Chart' })).toBeInTheDocument()
    expect(screen.getByRole('navigation')).toBeInTheDocument()
    expect(await screen.findByText(/API: ok v0\.4\.1/)).toBeInTheDocument()
  })

  it('renders the replay route', async () => {
    window.history.pushState({}, '', '/replay')
    render(<App />)

    expect(screen.getByRole('heading', { name: 'Replay' })).toBeInTheDocument()
  })
})
