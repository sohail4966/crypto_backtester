export const AUTH_TOKEN_STORAGE_KEY = 'auth_token'

/**
 * Dev-only credentials for silent local bootstrap.
 * Gated by `allowDevAuth()` — never used as the sole production auth path.
 */
export const DEV_USER_PASSWORD = 'dev-local-password'

/** Explicit opt-in via Vite env, or default on in `import.meta.env.DEV`. */
export function allowDevAuth(): boolean {
  const flag = import.meta.env.VITE_ALLOW_DEV_AUTH
  if (flag === 'true' || flag === '1') {
    return true
  }
  if (flag === 'false' || flag === '0') {
    return false
  }
  return Boolean(import.meta.env.DEV)
}
