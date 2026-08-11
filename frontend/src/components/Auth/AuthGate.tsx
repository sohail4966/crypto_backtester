import { useEffect, useState, type ReactNode } from 'react'
import { AuthModal } from '@/components/Auth/AuthModal'
import { AuthRequiredError, ensureUserId } from '@/services/userBootstrap'
import { useAuthStore } from '@/stores/authStore'

/**
 * Ensures a validated session before rendering authenticated app chrome.
 * In DEV (or VITE_ALLOW_DEV_AUTH), silent bootstrap may succeed without the modal.
 */
export function AuthGate({ children }: { children: ReactNode }) {
  const session = useAuthStore((s) => s.session)
  const [bootError, setBootError] = useState<string | null>(null)
  const [reloadToken, setReloadToken] = useState(0)
  const [booting, setBooting] = useState(true)

  useEffect(() => {
    let cancelled = false

    async function bootstrap() {
      setBootError(null)
      setBooting(true)
      try {
        await ensureUserId()
      } catch (error) {
        if (cancelled) {
          return
        }
        if (error instanceof AuthRequiredError) {
          useAuthStore.getState().setNeedsAuth()
          return
        }
        setBootError(
          error instanceof Error ? error.message : 'Failed to bootstrap session',
        )
      } finally {
        if (!cancelled) {
          setBooting(false)
        }
      }
    }

    void bootstrap()
    return () => {
      cancelled = true
    }
  }, [reloadToken])

  const needsModal = session === 'needs_auth' || session === 'expired'
  const ready = session === 'authenticated'

  if (bootError) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-3 p-6 text-center">
        <p className="text-sm text-text-secondary">{bootError}</p>
        <button
          type="button"
          className="rounded border border-border px-3 py-1.5 text-sm"
          onClick={() => setReloadToken((t) => t + 1)}
        >
          Retry
        </button>
      </div>
    )
  }

  return (
    <>
      {ready ? children : null}
      {!ready && !needsModal && booting ? (
        <div className="flex h-screen items-center justify-center text-sm text-text-secondary">
          Starting session…
        </div>
      ) : null}
      {needsModal ? (
        <AuthModal
          onAuthenticated={() => {
            setBootError(null)
            setReloadToken((t) => t + 1)
          }}
        />
      ) : null}
    </>
  )
}
