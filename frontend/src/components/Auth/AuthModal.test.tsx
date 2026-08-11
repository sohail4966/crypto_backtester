import { act, fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/services/userBootstrap', async () => {
  const actual = await vi.importActual<typeof import('@/services/userBootstrap')>(
    '@/services/userBootstrap',
  )
  return {
    ...actual,
    authenticateWithCredentials: vi.fn(),
    ensureUserId: vi.fn(),
  }
})

import { AuthModal } from '@/components/Auth/AuthModal'
import {
  PASSWORD_MIN_LENGTH_LOGIN,
  PASSWORD_MIN_LENGTH_REGISTER,
} from '@/constants/auth'

describe('AuthModal password policy (FE-L2-004)', () => {
  beforeEach(() => {
    vi.stubEnv('DEV', false)
    vi.stubEnv('VITE_ALLOW_DEV_AUTH', 'false')
  })

  it('login mode uses the loose BE login policy', () => {
    render(<AuthModal onAuthenticated={() => {}} />)
    const password = screen.getByLabelText(/password/i) as HTMLInputElement
    expect(password.minLength).toBe(PASSWORD_MIN_LENGTH_LOGIN)
  })

  it('register mode enforces the strict BE register policy (>=8)', async () => {
    const { getByRole } = render(<AuthModal onAuthenticated={() => {}} />)
    const registerTab = getByRole('button', { name: 'Register' })
    await act(async () => {
      fireEvent.click(registerTab)
    })
    const password = (await screen.findByLabelText(
      /password/i,
    )) as HTMLInputElement
    expect(password.minLength).toBe(PASSWORD_MIN_LENGTH_REGISTER)
    expect(PASSWORD_MIN_LENGTH_REGISTER).toBe(8)
  })
})
