import { useState, type FormEvent } from 'react'
import { allowDevAuth } from '@/constants/auth'
import {
  AuthRequiredError,
  authenticateWithCredentials,
  ensureUserId,
} from '@/services/userBootstrap'
import { useAuthStore } from '@/stores/authStore'

interface AuthModalProps {
  onAuthenticated: () => void
}

export function AuthModal({ onAuthenticated }: AuthModalProps) {
  const session = useAuthStore((s) => s.session)
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  const title = session === 'expired' ? 'Session expired' : 'Sign in'
  const subtitle =
    session === 'expired'
      ? 'Sign in again to continue.'
      : 'Sign in or create an account to use watchlists and authenticated APIs.'

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setPending(true)
    try {
      await authenticateWithCredentials({
        mode,
        email,
        password,
        name: mode === 'register' ? name : undefined,
      })
      onAuthenticated()
    } catch (cause) {
      const message =
        cause instanceof Error ? cause.message : 'Authentication failed'
      setError(message)
    } finally {
      setPending(false)
    }
  }

  async function continueAsDev() {
    setError(null)
    setPending(true)
    try {
      await ensureUserId()
      onAuthenticated()
    } catch (cause) {
      if (cause instanceof AuthRequiredError) {
        setError(cause.message)
      } else {
        setError(cause instanceof Error ? cause.message : 'Dev login failed')
      }
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="auth-modal-title"
        className="w-full max-w-md rounded-lg border border-border bg-surface p-6 shadow-lg"
      >
        <h2 id="auth-modal-title" className="text-lg font-semibold text-text">
          {title}
        </h2>
        <p className="mt-1 text-sm text-text-secondary">{subtitle}</p>

        <div className="mt-4 flex gap-2 text-sm">
          <button
            type="button"
            className={`rounded px-3 py-1.5 ${
              mode === 'login'
                ? 'bg-accent text-white'
                : 'border border-border text-text-secondary'
            }`}
            onClick={() => setMode('login')}
          >
            Login
          </button>
          <button
            type="button"
            className={`rounded px-3 py-1.5 ${
              mode === 'register'
                ? 'bg-accent text-white'
                : 'border border-border text-text-secondary'
            }`}
            onClick={() => setMode('register')}
          >
            Register
          </button>
        </div>

        <form className="mt-4 space-y-3" onSubmit={onSubmit}>
          {mode === 'register' ? (
            <label className="block text-sm">
              <span className="text-text-secondary">Name</span>
              <input
                className="mt-1 w-full rounded border border-border bg-background px-3 py-2 text-text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoComplete="name"
              />
            </label>
          ) : null}
          <label className="block text-sm">
            <span className="text-text-secondary">Email</span>
            <input
              type="email"
              required
              className="mt-1 w-full rounded border border-border bg-background px-3 py-2 text-text"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
            />
          </label>
          <label className="block text-sm">
            <span className="text-text-secondary">Password</span>
            <input
              type="password"
              required
              minLength={6}
              className="mt-1 w-full rounded border border-border bg-background px-3 py-2 text-text"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            />
          </label>

          {error ? (
            <p className="text-sm text-red-500" role="alert">
              {error}
            </p>
          ) : null}

          <button
            type="submit"
            disabled={pending}
            className="w-full rounded bg-accent px-3 py-2 text-sm font-medium text-white disabled:opacity-60"
          >
            {pending ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}
          </button>
        </form>

        {allowDevAuth() ? (
          <button
            type="button"
            disabled={pending}
            onClick={() => void continueAsDev()}
            className="mt-3 w-full rounded border border-border px-3 py-2 text-xs text-text-secondary hover:text-text disabled:opacity-60"
          >
            Continue as local demo (dev only)
          </button>
        ) : null}
      </div>
    </div>
  )
}
