# Agent E (Loop 2) — Frontend Solutions

**Date:** 2026-08-11
**Inputs:** `LOOP2_B_FRONTEND_ISSUES.md` (11 issues), `LOOP2_C_SEVERITY_DEPENDENCY.md` (severity/rank/dependency map).
**Purpose:** For each `FE-L2-*` issue, propose ≥2 concrete solutions and mark one as **Recommended** for Agent H to implement.

Every solution below is grounded in the current working tree (`frontend/src/**`) and cross-checked against `backend/api/**` where the FE ↔ BE contract matters (FE-L2-001/002/005/006).

---

## Summary — Recommended solution per issue

| Issue      | Recommended solution                                            |
|------------|-----------------------------------------------------------------|
| FE-L2-001  | Read `row.bar` (drop phantom `incomplete` gate)                 |
| FE-L2-002  | Surface `close.code` in `LiveWsClient`, wire 4401/4429 in hook  |
| FE-L2-003  | In-memory token + short-lived WS ticket (paired BE endpoint)    |
| FE-L2-004  | Shared password-policy constant driven by mode                  |
| FE-L2-005  | Rewrite `ScanRequest` type + `runScan` to match `ScanCreateRequest` |
| FE-L2-006  | Rewrite `AiClarifyRequest` / `AiExplainRequest` to BE schemas   |
| FE-L2-007  | Add `REPLAY_CLOSE_LIMIT = 4429` + `rate_limited` close-kind branch |
| FE-L2-008  | Reset `sessionId` + strip URL query in `useReplayWs` 4401 path  |
| FE-L2-009  | Reorder `WatchlistRoot` 401/403 to preserve `notifyAuthFailure` |
| FE-L2-010  | Partial resolve — drop unresolved IDs with a warning toast      |
| FE-L2-011  | Same-origin assertion in `resolveReplayWsUrl` (relative-only)   |

---

## Cross-issue implementation notes

- FE-L2-001, FE-L2-002 pair with **BE-L2-005** (OpenAPI live-WS doc). BE keeps its bar payload; the FE fixes are self-contained. Land in one PR titled "Live WS contract alignment".
- FE-L2-005, FE-L2-006 must land **after BE-L2-003** (OpenAPI security + missing route docs). Regenerate types once.
- FE-L2-003 requires a new BE endpoint (`POST /ws/tickets` or `Sec-WebSocket-Protocol` bearer). Agent D delivers the BE half; Agent H schedules FE-L2-003 in the same PR family and gates the migration behind an env flag until the BE side ships.
- FE-L2-004 depends on `backend/api/schemas/auth.py:34` (`min_length=8`). Bake into a shared FE constant so future BE changes are one-line.
- FE-L2-007 depends on **BE-L2-004** for the OpenAPI 4429 documentation. The FE constant + branch is independent, but the doc alignment should ship together.

---

## Issue-by-issue

### FE-L2-001: Live WS candle payload field mismatch (`bar` vs `candle`)
Severity: Important | Effort: S | Rank: 4

BE (`backend/api/ws/live.py:127-135`) emits:

```json
{ "type": "candle", "symbol": "...", "timeframe": "1m", "bar": { "time": ..., "open": ..., ... } }
```

FE (`frontend/src/services/liveWsClient.ts:51-79`) reads `row.candle`, short-circuits when `!candleRaw`, then also gates on a non-existent `row.incomplete` in `useLiveCandles` (`frontend/src/hooks/useLiveCandles.ts:26-28`). Net effect: `onCandle` never fires.

#### Solution 1: Read `row.bar` (drop the phantom `incomplete` gate)
- Approach: In `LiveWsClient.onmessage`, replace `const candleRaw = row.candle` with `const barRaw = row.bar`. Drop the `?? c.t`, `?? c.o`, ... shorthand key aliases — BE always emits the long-form `Bar` schema (`backend/api/schemas/candles.py:10-18`), so `Number(c.time)` etc. are sufficient. Remove `incomplete: Boolean(row.incomplete)` from the emitted payload and drop the `if (payload.incomplete) return` short-circuit in `useLiveCandles`. Also rename the `LiveWsHandlers.onCandle` payload's `candle` field for clarity, or keep it and just read from `row.bar` internally — the hook only cares about the assembled `OHLCVBar`.
- Pros/Cons:
  - + Surgical, single-file change (plus tiny hook edit).
  - + Matches OpenAPI `LiveWsCandleEvent` (`backend/docs/openapi.yaml:1434-1446`) exactly.
  - − Any external caller that relied on `incomplete` (there are none today) breaks.
- Files likely touched: `frontend/src/services/liveWsClient.ts`, `frontend/src/hooks/useLiveCandles.ts`, add a targeted test.

#### Solution 2: Dual-read (`bar` **or** `candle`) tolerant client
- Approach: Read `row.bar ?? row.candle` and only emit when either exists. Keep the `incomplete` boolean but default to `false` when absent.
- Pros/Cons:
  - + Forward/backward compatible if BE ever renames again or a stray legacy server responds with `candle`.
  - − Hides real contract drift — the exact class of bug we're fixing. Adds a permanent "just in case" branch with no BE counterpart.
  - − Doesn't remove the `incomplete` phantom flag; still contradicts the OpenAPI schema.
- Files likely touched: same as Solution 1.

#### Recommended: Solution 1
Justification: OpenAPI is authoritative and the BE code is stable. Solution 2 encodes ambiguity we don't have and would need to be rolled back later. Agent B's finding is explicitly about contract truth — Solution 1 fixes it.

Implementation notes for Agent H:
1. In `frontend/src/services/liveWsClient.ts`:
   - Rename local `candleRaw` → `barRaw`; read `row.bar`.
   - Drop the shorthand OHLCV key aliases (`c.t`, `c.o`, ...) — BE never emits them; keep only the long names.
   - Remove `incomplete?: boolean` from `LiveWsHandlers.onCandle` payload type.
2. In `frontend/src/hooks/useLiveCandles.ts`:
   - Remove the `if (payload.incomplete) return` guard.
3. Add a test in `frontend/src/services/liveWsClient.test.ts` (create if missing) that pushes `{"type":"candle","symbol":"BTC/USDT","timeframe":"1m","bar":{...}}` and asserts `onCandle` fires with the expected `OHLCVBar`.

---

### FE-L2-002: `LiveWsClient` discards close code — no 4401 / 4429 handling
Severity: Important | Effort: S | Rank: 5

`socket.onclose = () => this.handlers.onClose?.()` (`liveWsClient.ts:86-91`) drops `event.code`. `useLiveCandles` doesn't even wire `onClose`. Expired JWT (4401) and per-user cap (4429) are both invisible.

#### Solution 1: Adopt the `ReplayWsClient` `onClose({ code, reason, kind })` shape
- Approach: Change `LiveWsHandlers.onClose` signature to `(info: { code: number; reason: string; kind: 'unauthorized' | 'rate_limited' | 'closed' | 'error' }) => void`. Copy the `closeKind` function from `replayWsClient.ts` (or extract it to `frontend/src/services/wsCloseCode.ts` — see FE-L2-007). Wire `useLiveCandles` to call `notifyAuthFailure('UNAUTHORIZED')` on `kind === 'unauthorized'` and `showToast('Too many concurrent connections')` on `kind === 'rate_limited'`.
- Pros/Cons:
  - + Symmetric with the replay-WS pipeline; single mental model.
  - + Enables shared close-code map (see FE-L2-007), reused by both clients.
  - − Slightly larger surface — `LiveWsClient` consumers must update the onClose signature. Only `useLiveCandles` consumes it today, so blast radius is one file.
- Files likely touched: `frontend/src/services/liveWsClient.ts`, `frontend/src/hooks/useLiveCandles.ts`, new `frontend/src/services/wsCloseCode.ts` (or share via constants), tests.

#### Solution 2: Minimal `onClose(code, reason)` callback (no `kind` helper)
- Approach: Change `onClose` to `(code: number, reason: string) => void`. Push all classification logic into `useLiveCandles`. Detect `code === 4401` → `notifyAuthFailure`; `code === 4429` → toast; everything else → silent.
- Pros/Cons:
  - + Smallest change — one signature edit.
  - − Duplicates close-code semantics between replay and live paths. Any future 4xxx code (e.g. planned `WS_QUOTA`, `WS_KILLED`) has to be added twice.
  - − No natural place to test the classifier in isolation.
- Files likely touched: `frontend/src/services/liveWsClient.ts`, `frontend/src/hooks/useLiveCandles.ts`.

#### Recommended: Solution 1
Justification: The replay pipeline already proves this shape works and Agent B explicitly calls out that live-WS should follow the replay pattern (`useReplayWs.ts:151-189` is the reference). Extracting a shared `wsCloseCode` helper also unlocks FE-L2-007 cleanly.

Implementation notes for Agent H:
1. Add `frontend/src/services/wsCloseCode.ts` exporting `WS_CLOSE_UNAUTHORIZED = 4401`, `WS_CLOSE_RATE_LIMITED = 4429`, and a `classifyWsCloseKind(code)` helper returning `'unauthorized' | 'rate_limited' | 'superseded' | 'not_found' | 'closed' | 'error'`. Re-export the replay constants from `constants/replay.ts` for backward-compat.
2. Update `LiveWsClient.onclose` to invoke `handlers.onClose?.({ code: event.code, reason: event.reason, kind: classifyWsCloseKind(event.code) })`.
3. In `useLiveCandles`, pass `onClose: ({ kind }) => { if (kind === 'unauthorized') notifyAuthFailure('UNAUTHORIZED'); else if (kind === 'rate_limited') showToast('Too many concurrent WebSocket connections'); }`. Use `useToast` like `useReplayWs` does.
4. Add a `liveWsClient.test.ts` case: simulate close(4401) → asserts handler gets `kind === 'unauthorized'`; close(4429) → `'rate_limited'`.

---

### FE-L2-003: JWT stored in `localStorage` and appended as `?token=` on every WS URL
Severity: Important | Effort: L | Rank: 14

FE stores JWT in `localStorage` (`authToken.ts:1-17`) and both `resolveLiveWsUrl` / `resolveReplayWsUrl` append `token=<jwt>` to the URL, leaking it into DevTools, HAR exports, referer headers, and browser history. Requires a paired BE change (Agent D delivers `POST /ws/tickets`).

#### Solution 1: In-memory JWT + short-lived one-shot WS ticket (`POST /ws/tickets`)
- Approach:
  - **Storage:** Split `authToken.ts` into a two-tier store — primary in-memory (`let currentToken: string | null = null`), fallback `sessionStorage` (auto-cleared on tab close) for reloads only when the tab is trusted. Never touch `localStorage` for the JWT. Persist a signed-in-hint in `localStorage` (userId, `hint = "signed_in"`) so the app still knows to try `GET /auth/me` on reload. On reload with an empty in-memory token, treat the session as `unknown` and either (a) let AuthGate prompt again (production) or (b) rely on the future silent-refresh path (deferred).
  - **WS auth:** Before opening a WebSocket, call `POST /api/v1/ws/tickets` (Bearer JWT via `apiRequest`) → returns `{ ticket: "<opaque, single-use>", ttl_seconds: 30 }`. Append `?ticket=<opaque>` (not `token=`) to the WS URL. BE-side, the ticket is redeemable once against `session:{user_id}`. Old `?token=` support is removed from FE (BE can keep it for backward-compat behind a feature flag).
  - **Feature gating:** Add `VITE_WS_TICKET=true` flag; when false, FE falls back to the current `?token=` path so we can land the FE changes ahead of / behind the BE endpoint.
- Pros/Cons:
  - + JWT never appears in a URL, DevTools column, HAR, or browser history.
  - + In-memory token means XSS still needs to intercept the fetch/response, not just read `localStorage`.
  - + Ticket TTL bounds replay-attack window even if the ticketed URL is logged.
  - − Requires a new BE endpoint (Agent D). Cannot ship as FE-only.
  - − Reloads without silent-refresh force re-login — need to decide the UX (a follow-up refresh-token path is out of scope for L2).
  - − Slightly more moving parts (`ws/tickets` client, ticket cache, retry on 401 → ticket refresh).
- Files likely touched: `frontend/src/services/authToken.ts`, new `frontend/src/services/wsTicket.ts`, `frontend/src/services/liveWsClient.ts`, `frontend/src/services/replayWsClient.ts`, `frontend/src/services/userBootstrap.ts` (session probe), `frontend/src/stores/authStore.ts`, tests. Plus BE endpoint (Agent D).

#### Solution 2: `Sec-WebSocket-Protocol` bearer subprotocol
- Approach: Instead of a query token, pass the JWT via the `Sec-WebSocket-Protocol` header. Browser `WebSocket` API accepts subprotocols as the second arg: `new WebSocket(url, ['bearer.jwt.v1', token])`. BE `WebSocketRoute` inspects `request.headers['sec-websocket-protocol']`, extracts the token, and echoes the protocol on accept. Keep in-memory token storage (same as Solution 1).
- Pros/Cons:
  - + Token doesn't appear in URL or HAR entry's `url` column.
  - + Zero extra round-trip vs Solution 1's `POST /ws/tickets`.
  - − Some proxies / reverse proxies strip or refuse arbitrary `Sec-WebSocket-Protocol` values; production ops risk.
  - − BE still ends up with a long-lived JWT on the socket handshake; no TTL reduction. If the socket handshake is ever logged with headers, we're back to the same leak class.
  - − Non-standard convention; Sentry/RUM instrumentation of WS often doesn't understand it.
  - − Still needs BE work (parse subprotocol; the current `resolve_ws_token` in `backend/api/deps.py:159-166` doesn't).
- Files likely touched: same as Solution 1 minus `wsTicket.ts`; add subprotocol parsing to BE.

#### Recommended: Solution 1
Justification: Agent C explicitly calls out `POST /ws/tickets` as the intended pairing. Ticket approach also bounds replay window (30 s TTL) which subprotocol does not, and gets past reverse proxies that block non-standard subprotocol values (Cloudflare, some ALBs). Extra endpoint is one router + one repo table row (Agent D's remit).

Implementation notes for Agent H:
1. Rewrite `frontend/src/services/authToken.ts`:
   - Keep `AUTH_TOKEN_STORAGE_KEY` for the sign-in **hint** only (value `"signed_in"`, no JWT).
   - Add module-level `let inMemoryToken: string | null = null` with `getAuthToken()`, `setAuthToken(t)`, `clearAuthToken()`.
   - Migrate reads: bootstrap on load reads legacy `localStorage.getItem('auth_token')` once, calls `setAuthToken(...)` into memory, then `localStorage.removeItem('auth_token')` — this drains old sessions cleanly.
2. Add `frontend/src/services/wsTicket.ts`:
   ```ts
   let cached: { ticket: string; exp: number } | null = null
   export async function getWsTicket(): Promise<string> {
     const now = Date.now() / 1000
     if (cached && cached.exp - now > 3) return cached.ticket
     const resp = await apiRequest<{ ticket: string; ttl_seconds: number }>('/ws/tickets', { method: 'POST' })
     cached = { ticket: resp.ticket, exp: now + resp.ttl_seconds }
     return resp.ticket
   }
   export function clearWsTicket(): void { cached = null }
   ```
   Also clear cache from `notifyAuthFailure` (via a hook in `authSession.ts`).
3. In `liveWsClient.ts` and `replayWsClient.ts`, replace `appendToken` with an async `appendTicket` that awaits `getWsTicket()`. Because `WebSocket` constructor is synchronous, restructure `connect()` to `await getWsTicket()` before `new WebSocket(url)`. Both clients already have async-friendly consumers (`useLiveCandles`, `useReplayWs`), so exposing an `async connect()` is safe.
4. Gate behind `VITE_WS_TICKET === 'true'`; when off, fall back to current `?token=` path so FE can be merged incrementally.
5. Coordinate with Agent D: BE `POST /ws/tickets` returns `{ticket, ttl_seconds}`, `resolve_ws_token(websocket, token)` in `backend/api/deps.py` is extended to also accept `?ticket=` and consumes it once.
6. Tests: `authToken.test.ts` covers legacy-drain path; `wsTicket.test.ts` covers TTL caching; `liveWsClient.test.ts` / `replayWsClient.test.ts` assert `?ticket=` (not `token=`) on the connect URL under the flag.

---

### FE-L2-004: Register password `minLength={6}` contradicts BE `min_length=8`
Severity: Minor | Effort: S | Rank: 15

`AuthModal.tsx:130-138` uses `minLength={6}` for both login and register modes. BE `AuthRegisterRequest.password` (`backend/api/schemas/auth.py:34`) requires `min_length=8`.

#### Solution 1: Shared constant + mode-driven minLength
- Approach: Add `PASSWORD_MIN_LENGTH_REGISTER = 8` and `PASSWORD_MIN_LENGTH_LOGIN = 6` (or `1`, matching BE `AuthLoginRequest.password: min_length=1`) to `frontend/src/constants/auth.ts`. Change `AuthModal`'s input to `minLength={mode === 'register' ? PASSWORD_MIN_LENGTH_REGISTER : PASSWORD_MIN_LENGTH_LOGIN}`. Also update the inline error message (or add one) so users see "Password must be at least 8 characters" before submit.
- Pros/Cons:
  - + Single source of truth for FE; BE change = one FE constant edit.
  - + Prevents the raw 422 pydantic message ("String should have at least 8 characters") from reaching the UI.
  - − Still not automatically synced with BE — if `.env`-tunable in the future, needs a config surface.
- Files likely touched: `frontend/src/constants/auth.ts`, `frontend/src/components/Auth/AuthModal.tsx`.

#### Solution 2: Hardcode `minLength={8}` unconditionally
- Approach: Change `minLength={6}` → `minLength={8}` for both modes.
- Pros/Cons:
  - + One-character diff.
  - − Login form now rejects legacy 6/7-char passwords locally before even hitting the BE, which happily accepts them (BE login has `min_length=1`). Users with old-format passwords would be locked out of the UI.
  - − No constant to share; drift risk stays.
- Files likely touched: `frontend/src/components/Auth/AuthModal.tsx`.

#### Recommended: Solution 1
Justification: The mode-aware form matches the BE policy exactly (`min_length=8` for register, `min_length=1` for login) and gives us a single constant to bump if BE ever raises the bar. Solution 2 is a foot-gun for existing users.

Implementation notes for Agent H:
1. Extend `frontend/src/constants/auth.ts`:
   ```ts
   export const PASSWORD_MIN_LENGTH_REGISTER = 8
   export const PASSWORD_MIN_LENGTH_LOGIN = 1
   ```
2. In `AuthModal.tsx`, replace `minLength={6}` with `minLength={mode === 'register' ? PASSWORD_MIN_LENGTH_REGISTER : PASSWORD_MIN_LENGTH_LOGIN}`.
3. (Optional polish) Add a small hint below the input in register mode: `"At least ${PASSWORD_MIN_LENGTH_REGISTER} characters"`.
4. Add an `AuthModal.test.tsx` case (or extend existing) asserting that submitting `password: "abcdefg"` (7 chars) in register mode fails HTML validation and does not call `authenticateWithCredentials`.

---

### FE-L2-005: `scanApi.ts` request shape drifted from `ScanCreateRequest`
Severity: Important | Effort: M | Rank: 10

`ScanRequest` today: `{ symbols, timeframe (scalar), start, end, strategy_name? }`. BE `ScanCreateRequest` (`backend/api/schemas/scan.py:13-33`): `{ timeframes: list[str] (≥1), start, end, condition, symbols?, alert_trigger, persist }`. Client is guaranteed to 422 on first real call.

#### Solution 1: Rewrite `ScanRequest` + `runScan` to mirror the BE schema exactly (recommended path)
- Approach: Delete `strategy_name`. Rename `timeframe` → `timeframes: string[]` (min 1). Add required `condition: Record<string, unknown>` (opaque DSL blob — FE doesn't own the shape, it's whatever `translate` / `explain` returns from `/ai/*`). Add optional `symbols?: string[]`, `alert_trigger?: 'edge' | 'level'` (default `'edge'`), `persist?: boolean` (default `true`). Update `ScanResponse` to match `ScanRunResponse` — snake_case fields (`scan_id`, `alert_count`, `duration_ms`, `scanned_pairs`, `persisted`, `matches`, `errors`, `timeframes`, `symbols`, `start`, `end`, `alert_trigger`). Drop the ambiguous `scanId` alias and `[key: string]: unknown` catch-all now that the contract is stable.
- Pros/Cons:
  - + Zero drift with BE. First real POST succeeds.
  - + Makes the client usable by future scan UI without more edits.
  - − Any downstream reader of `ScanResponse.results` (there are none today) breaks; needs a `matches`-shaped test.
- Files likely touched: `frontend/src/services/scanApi.ts`, add `frontend/src/services/scanApi.test.ts`.

#### Solution 2: Keep the current shape and add a `toScanCreateRequest` adapter
- Approach: Leave `ScanRequest` alone as a "friendly" FE shape. Inside `runScan`, translate `timeframe` → `[timeframe]` and inject a placeholder `condition` derived from `strategy_name`. Add `symbols?`, `alert_trigger?`, `persist?` as optional overrides.
- Pros/Cons:
  - + Backward compatible for callers of `ScanRequest` (there are none, per Agent B's Grep).
  - − Requires the FE to invent a `condition` payload it can't legitimately construct (BE `condition` is a DSL blob from `/ai/translate`, not derivable from a `strategy_name` string). The endpoint will still 422.
  - − Two shapes to maintain; the "friendly" one lies to callers about what the BE accepts.
- Files likely touched: same as Solution 1.

#### Recommended: Solution 1
Justification: There are no callers today (`Grep` confirms zero `runScan` invocations). This is a pure API-surface fix, so aligning with the BE schema now is free and prevents Solution 2's placeholder-`condition` guesswork. Also cleanly composes with FE-L2-006's `AiExplainRequest = { strategy: {...} }` — the same `condition` blob threads through both clients.

Implementation notes for Agent H:
1. Schedule **after** BE-L2-003 (OpenAPI truthing) so any codegen reflects the corrected `/scan` docs.
2. Rewrite `frontend/src/services/scanApi.ts`:
   ```ts
   export type ScanCreateRequest = {
     timeframes: string[]
     start: number
     end: number
     condition: Record<string, unknown>
     symbols?: string[]
     alert_trigger?: 'edge' | 'level'
     persist?: boolean
   }
   export type ScanMatch = { symbol: string; timeframe: string; bar_ts: string; triggered: boolean; close: number | null }
   export type ScanError = { symbol: string; timeframe: string; error: string }
   export type ScanRunResponse = {
     scan_id: string | null
     timeframes: string[]
     symbols: string[]
     start: number
     end: number
     alert_trigger: 'edge' | 'level'
     matches: ScanMatch[]
     alert_count: number
     duration_ms: number
     scanned_pairs: number
     errors: ScanError[]
     persisted: boolean
   }
   export function runScan(body: ScanCreateRequest): Promise<ScanRunResponse> { ... }
   export function getScan(scanId: string): Promise<ScanRunResponse> { ... }
   ```
3. Add `scanApi.test.ts` mirroring `backtestApi.test.ts` — asserts POST body shape and that snake_case response fields survive typing (no camel-case conversion).
4. Grep for `ScanRequest` / `ScanResponse` before/after; there should be zero non-test callers (confirmed by Agent B).

---

### FE-L2-006: `aiApi.ts` clarify/explain payloads mismatched with BE
Severity: Important | Effort: M | Rank: 11

BE (`backend/api/schemas/ai.py:18-28`): `ClarifyRequest = { session_id (min 1), answers: dict[str, str] (min 1) }`; `ExplainRequest = { strategy: dict }`. FE (`aiApi.ts`): `AiClarifyRequest = { message, session_id? }`; `AiExplainRequest = { run_id?, context? }`. Both wrong. `AiTranslateRequest` is correct.

#### Solution 1: Rewrite FE types to match BE schemas exactly
- Approach:
  - `AiClarifyRequest = { session_id: string; answers: Record<string, string> }` — both required.
  - `AiExplainRequest = { strategy: Record<string, unknown> }` — required (the DSL blob from `translate`).
  - Add narrow response types: `AiTranslateResponse` as a discriminated union of `{ status: 'ok'; strategy; explanation }` and `{ status: 'needs_clarification'; session_id; questions: ClarificationQuestion[] }`; `AiExplainResponse = { explanation: string }`.
  - Optionally rename to drop the `Ai` prefix (matches BE), or keep for consistency with `aiApi.ts` filename.
- Pros/Cons:
  - + Matches BE exactly, including `TranslateOkResponse` / `TranslateClarifyResponse` discrimination.
  - + Unlocks a downstream typed clarify UI without any more contract fixes.
  - − Slightly larger diff than a one-line rename; still trivial.
- Files likely touched: `frontend/src/services/aiApi.ts`, add `frontend/src/services/aiApi.test.ts`.

#### Solution 2: Rename fields only, keep loose typing
- Approach: Rename `message` → `answers` (as `Record<string, string>`); rename `run_id`/`context` → `strategy` (as `unknown`). Don't touch response types.
- Pros/Cons:
  - + Minimum change.
  - − Response is still `Promise<unknown>` — every future clarify consumer has to re-derive the shape. FE-L2-006 was as much about the response envelope (translate can return `ok` or `needs_clarification`) as the request; leaving it untyped just moves the drift.
- Files likely touched: `frontend/src/services/aiApi.ts`.

#### Recommended: Solution 1
Justification: BE has a well-defined discriminated union on `/ai/translate`; the FE deserves the typed union. Same reasoning as FE-L2-005 — no callers today (`Grep` confirms), so this is a free contract fix. Both `aiExplain` and `runScan` share the `condition`/`strategy` DSL blob type, so typing them together prevents copy-paste drift.

Implementation notes for Agent H:
1. Schedule **after** BE-L2-003 (OpenAPI security + AI security blocks).
2. Rewrite `frontend/src/services/aiApi.ts`:
   ```ts
   export type AiTranslateRequest = { text: string }
   export type ClarificationQuestion = { id: string; prompt: string; options: string[] }
   export type AiTranslateResponse =
     | { status: 'ok'; strategy: Record<string, unknown>; explanation: string }
     | { status: 'needs_clarification'; session_id: string; questions: ClarificationQuestion[] }
   export type AiClarifyRequest = { session_id: string; answers: Record<string, string> }
   export type AiExplainRequest = { strategy: Record<string, unknown> }
   export type AiExplainResponse = { explanation: string }

   export function aiTranslate(body: AiTranslateRequest): Promise<AiTranslateResponse> { ... }
   export function aiClarify(body: AiClarifyRequest): Promise<AiTranslateResponse> { ... }
   export function aiExplain(body: AiExplainRequest): Promise<AiExplainResponse> { ... }
   ```
3. Add `aiApi.test.ts` — asserts POST bodies match BE, and translate response can be narrowed on `status`.
4. If any test references the old shapes, migrate them.

---

### FE-L2-007: Replay + Live WS 4429 collapses to a generic "connection lost" UX
Severity: Minor | Effort: S | Rank: 22

`replayWsClient.closeKind` (`replayWsClient.ts:48-62`) only maps 4401/4402/4404/1000/1001; every other code (including 4429 `WS_LIMIT`) becomes `'error'` → generic toast. `LiveWsClient` doesn't surface the code at all (see FE-L2-002).

#### Solution 1: Add `REPLAY_CLOSE_LIMIT = 4429` + a `rate_limited` close-kind branch on both clients
- Approach:
  - Add constants:
    ```ts
    export const REPLAY_CLOSE_LIMIT = 4429
    ```
    in `frontend/src/constants/replay.ts`, and a matching `WS_CLOSE_RATE_LIMITED = 4429` in the shared helper from FE-L2-002.
  - Extend `ReplayWsCloseReason` with `'rate_limited'`. Update `closeKind()` to return `'rate_limited'` on 4429.
  - In `useReplayWs.ts` `onClose`, add a branch: `else if (kind === 'rate_limited') { store.setConnection('red', 'rate_limited'); showToast('Too many concurrent WebSocket connections') }`.
  - `useLiveCandles` (per FE-L2-002 recommended approach) already gets the same shape — just add the same `rate_limited` toast.
- Pros/Cons:
  - + Distinct UX branch matching the BE contract (`backend/api/deps.py:140-149`).
  - + Same shared helper serves live + replay.
  - − Requires a small addition to `useReplayStore`'s connection reason type (`'rate_limited'` alongside existing reasons). Minor churn.
- Files likely touched: `frontend/src/constants/replay.ts` (or the new `wsCloseCode.ts`), `frontend/src/services/replayWsClient.ts`, `frontend/src/hooks/useReplayWs.ts`, `frontend/src/hooks/useLiveCandles.ts`, `frontend/src/stores/replayStore.ts` (type widening).

#### Solution 2: Custom-message-only fallback (no new kind)
- Approach: Leave `closeKind` unchanged, but in the `'error'` branch inspect `event.reason` (already `'WS_LIMIT'` per BE) and toast a specific message when `reason === 'WS_LIMIT'`.
- Pros/Cons:
  - + Minimal diff.
  - − Overloads the `'error'` state; connection banner still says generic red.
  - − Couples the fix to a stringly-typed reason. If BE ever tweaks the reason text, FE UX regresses silently.
- Files likely touched: `frontend/src/hooks/useReplayWs.ts`, `frontend/src/hooks/useLiveCandles.ts`.

#### Recommended: Solution 1
Justification: Numeric close codes are stable BE contract (documented in `backend/api/deps.py:140-149`); reason strings are not. Adding a dedicated `rate_limited` kind pairs cleanly with the shared helper introduced in FE-L2-002. Agent B's fix suggestion is explicitly Solution 1.

Implementation notes for Agent H:
1. Land after FE-L2-002 so `wsCloseCode.ts` exists; otherwise mirror the constant in `constants/replay.ts` only.
2. Extend `ReplayWsCloseReason` to include `'rate_limited'`; extend `closeKind` to map 4429.
3. In `useReplayWs.ts` `onClose`, before the `else if (kind === 'error')` branch, add:
   ```ts
   else if (kind === 'rate_limited') {
     client.clearQueue()
     store.setConnection('red', 'rate_limited')
     showToast('Too many concurrent WebSocket connections')
   }
   ```
4. In `useLiveCandles`, add the same toast on `kind === 'rate_limited'`.
5. Depends on BE-L2-004 for OpenAPI doc alignment; not a code blocker.
6. Test: extend `replayWsClient.test.ts` (or `useReplayWs.test.ts`) with a 4429 close case.

---

### FE-L2-008: On WS 4401, replay `sessionId` + URL param stay set → 4404 cascade
Severity: Minor | Effort: S | Rank: 19

`useReplayWs`'s `unauthorized` branch (`useReplayWs.ts:151-161`) calls `notifyAuthFailure('UNAUTHORIZED')`, sets phase to `paused` and error to "Authentication required", but does not touch `sessionId`, `wsUrl`, or the `replaySession` URL param. Post re-auth, `useReplaySession`'s URL-resume effect re-issues `beginConnect` → 404/4404 cascade.

#### Solution 1: Reset store + strip URL param inside the `unauthorized` branch of `useReplayWs`
- Approach: Extend the unauthorized close handler to also (a) call `useReplayStore.getState().reset()` (or a narrower `resetForAuth()` that clears `sessionId`, `wsUrl`, `error` but preserves `speed`), and (b) invoke a callback (`onUnauthorized?()`) that `useReplaySession` wires to `writeSessionParam(null)`. Keep the toast + `notifyAuthFailure` calls as-is.
- Pros/Cons:
  - + Behavior mirrors "session expired" everywhere else — post modal-dismiss, replay is fully inactive.
  - + `useReplaySession`'s existing URL-resume effect (`useReplaySession.ts:214-276`) no longer sees a stale `replaySession=` param.
  - − Adds a new prop (`onUnauthorized`) to `useReplayWs`, symmetric to `onSuperseded`/`onNotFound`.
  - − If the user re-authenticates as the same user, the session is *technically* still recoverable BE-side. Solution 1 chooses "safer default: force restart from picker" over "attempt to re-attach".
- Files likely touched: `frontend/src/hooks/useReplayWs.ts`, `frontend/src/hooks/useReplaySession.ts`, `frontend/src/stores/replayStore.ts` (add `resetForAuth` if desired).

#### Solution 2: Move the reset into `useReplaySession` via existing `onNotFound`-style callback plumbing
- Approach: Instead of `useReplayWs` calling into the store, add `onUnauthorized?()` to `UseReplayWsOptions`. `useReplaySession` wires it to `writeSessionParam(null)` + `useReplayStore.getState().reset()` (same as Solution 1's effect) but the store mutation lives with the session orchestrator.
- Pros/Cons:
  - + Cleaner separation — `useReplayWs` stays pure "transport", `useReplaySession` owns lifecycle.
  - + Matches the existing pattern for `onSuperseded` / `onNotFound`.
  - − Two file edits instead of one, but each is smaller.
- Files likely touched: same as Solution 1.

#### Recommended: Solution 2
Justification: The codebase already has an established pattern (`onSuperseded`, `onNotFound` in `useReplayWs`) for exactly this hand-off — Solution 2 is symmetric with that. It also keeps `useReplayWs` transport-focused and leaves URL-mutation exclusively to `useReplaySession`, which owns `writeSessionParam`.

Implementation notes for Agent H:
1. Add `onUnauthorized?: () => void` to `UseReplayWsOptions` (`useReplayWs.ts`).
2. In the `unauthorized` close-branch, after `notifyAuthFailure` and toast:
   ```ts
   client.clearQueue()
   store.setConnection('red', 'unauthorized')
   store.setPhase('paused')
   store.setError('Authentication required')
   showToast('Session expired — sign in again')
   notifyAuthFailure('UNAUTHORIZED')
   onUnauthorized?.()
   ```
3. In `useReplaySession.ts`, pass `onUnauthorized` to `useReplayWs`:
   ```ts
   useReplayWs({
     registerWsClient,
     onSuperseded: () => { /* existing */ },
     onNotFound: () => { /* existing */ },
     onUnauthorized: () => {
       writeSessionParam(null)
       useReplayStore.getState().reset()
     },
   })
   ```
4. Also clear the `resumeAttemptedRef` in the same handler (`resumeAttemptedRef.current = null`) so a subsequent same-URL bookmark can retry after re-auth.
5. Test: extend `useReplayWs.test.ts` or `useReplaySession.test.ts` — close(4401) triggers URL-param clear.

---

### FE-L2-009: `WatchlistRoot` 401/403 handler wipes the `expired` reason
Severity: Minor | Effort: S | Rank: 18

`apiRequest` calls `notifyAuthFailure(code)` on 401/403 → `authStore.session = 'expired'`, `lastErrorCode = code` (`authSession.ts:16-35`). `WatchlistRoot` then calls `clearStaleUser(userId)` → `clearLocalUserId()` → `authStore.clear()` (`authStore.ts:59-66`), which resets `session` to `'unknown'` and wipes `lastErrorCode`. Then it calls `setNeedsAuth()` — `session = 'needs_auth'`, still no error code. AuthModal shows "Sign in" instead of "Session expired" (`AuthModal.tsx:23-27`).

#### Solution 1: Reorder — do not call `clearLocalUserId()` (which resets the store) on the unauthorized branch
- Approach: In the `isUnauthorized` branch of `WatchlistRoot.tsx:170-193`, skip the `clearStaleUser + clearLocalUserId` sequence entirely (since `apiRequest` already cleared the token via `notifyAuthFailure`). Just call `useAuthStore.getState().setNeedsAuth` **only if** `authStore.session !== 'expired'`; otherwise let the `expired` state (with its `lastErrorCode`) stand. Also swap in a targeted watchlist-cache flush (`deleteWatchlistCache(userId)`) instead of the full store reset.
- Pros/Cons:
  - + Preserves the `expired` reason set by `apiRequest`, so `AuthModal` shows "Session expired".
  - + Still clears the watchlist cache for the stale user.
  - − Requires care that other paths (USER_NOT_FOUND) still get the full clear behavior.
- Files likely touched: `frontend/src/components/Watchlist/WatchlistRoot.tsx`, potentially `frontend/src/services/userBootstrap.ts` (add a `clearStaleWatchlistCache(userId)` helper that doesn't touch the auth store).

#### Solution 2: Make `authStore.clear()` preserve `lastErrorCode` when the current session is `'expired'`
- Approach: In `authStore.ts`'s `clear()`, if `state.session === 'expired'`, keep `session` and `lastErrorCode`; otherwise reset. Alternatively make `setNeedsAuth()` preserve `lastErrorCode` if `session === 'expired'`.
- Pros/Cons:
  - + One-file change; fixes any current or future caller that does `clear()` after `notifyAuthFailure`.
  - − Adds hidden conditional in the store; violates the "explicit state transitions" mental model of the current `authStore`.
  - − Doesn't fix the semantic that `WatchlistRoot` is doing an unnecessary `clearLocalUserId()` after `apiRequest` already cleared the token; that duplication stays.
- Files likely touched: `frontend/src/stores/authStore.ts`.

#### Recommended: Solution 1
Justification: The bug is order-of-operations in `WatchlistRoot`, not a store-shape issue. Solution 2 papers over it and locks in the duplicated clear. Solution 1 aligns `WatchlistRoot` with the pattern `apiRequest` already established: on 401/403 with a token present, `apiRequest → notifyAuthFailure` is authoritative; the caller should react to `session === 'expired'`, not re-drive the auth store.

Implementation notes for Agent H:
1. In `frontend/src/components/Watchlist/WatchlistRoot.tsx`, inside the `isUnauthorized` branch (approx lines 179-192):
   - Remove `await clearStaleUser(userId)` + `clearLocalUserId()` in the unauthorized path.
   - Replace with a targeted `deleteWatchlistCache(userId)` call (add an export if not present) so the stale watchlist cache is dropped.
   - Do **not** call `useAuthStore.getState().setNeedsAuth()` unconditionally — check `useAuthStore.getState().session !== 'expired'` first.
2. Keep the existing `USER_NOT_FOUND` branch untouched (it correctly clears everything for a truly missing user).
3. Also drop the `staleRecoveryUsedRef.current = true` on unauthorized — the retry loop isn't relevant when the token itself is the problem; the auth modal handles the retry.
4. Add a `WatchlistRoot.test.tsx` case: mock `listWatchlists` to throw `ApiError(401)` → assert `useAuthStore.getState()` ends at `{ session: 'expired', lastErrorCode: 'UNAUTHORIZED' }` and `AuthModal` renders "Session expired".

---

### FE-L2-010: `resolveWatchlistDtos` hard-fails the whole refresh on any unresolved symbol id
Severity: Minor | Effort: S | Rank: 23

`resolveWatchlistDtos` (`watchlistNormalize.ts:99-133`) throws `SymbolResolveError` if a single ID stays unresolved after active-catalog + `getSymbol` fallback. In `WatchlistRoot.tsx`, this bubbles into the generic error branch → whole watchlist panel goes red.

#### Solution 1: Partial-resolve — drop unresolved IDs and surface a soft warning
- Approach: Rewrite the final loop in `resolveWatchlistDtos` to skip unresolved IDs (`byId.get(id)` returning `undefined`) rather than throw. Return `{ watchlists: Watchlist[]; unresolved: string[] }` (or add an optional `onUnresolved(ids)` callback so callers can toast). `WatchlistRoot` fires a soft `showToast('Some symbols could not be loaded and were hidden')` when `unresolved.length > 0` but still applies the (partial) canonical list. Keep `SymbolResolveError` as a hard error only when **every** ID for a **single** watchlist fails (i.e. all symbols unresolved) — that indicates a real BE outage, not stale data.
- Pros/Cons:
  - + Panel keeps rendering; single delisted pair no longer nukes everyone.
  - + Signals data quality via a toast so the user isn't confused.
  - − Slightly larger API change on the utility. Callers that expected the throw need updating (only `WatchlistRoot.addSymbolToSelected` and `createWatchlist` fallbacks).
- Files likely touched: `frontend/src/utils/watchlistNormalize.ts`, `frontend/src/components/Watchlist/WatchlistRoot.tsx`, `frontend/src/utils/watchlistNormalize.test.ts` (if present).

#### Solution 2: Broaden the active-catalog fallback (`active_only=false` for the `getSymbol` path)
- Approach: Keep `resolveWatchlistDtos` semantics; instead, change the fallback `getSymbol(id)` call to explicitly hit `active_only=false` (add a new `searchSymbols(query, { activeOnly: false })` overload, or a new `getSymbolIncludingInactive(id)` that skips the `active_only` filter). The idea is: `getSymbol` already fetches by id (`chartDataAdapter.ts:101-103`), so if BE returns inactive symbols on `/symbols/{id}`, IDs stay resolvable.
- Pros/Cons:
  - + Behavior stays "all or nothing" — no per-symbol drops.
  - + Best for the case where the symbol is inactive but still exists.
  - − Doesn't help if the BE returns 404 for truly deleted symbols. Any real deletion still nukes the panel.
  - − Requires a BE-side check: does `GET /symbols/{id}` currently filter by active? (`chartDataAdapter.ts` doesn't pass `active_only`; the endpoint may already return inactive. If so, this solution is a no-op.)
- Files likely touched: `frontend/src/services/chartDataAdapter.ts`, possibly none if `getSymbol` already returns inactive.

#### Recommended: Solution 1
Justification: Real-world watchlist durability requires "one bad row shouldn't nuke the panel." Solution 2 helps for inactive-but-existing symbols but doesn't help for hard 404s and doesn't communicate the data-quality issue to the user. Solution 1 does both and is the standard pattern for FE resilience against BE catalog churn.

Implementation notes for Agent H:
1. Rewrite `resolveWatchlistDtos`'s return path:
   ```ts
   const unresolved: string[] = []
   const watchlists = dtos.map((dto) => {
     const symbols: Symbol[] = []
     for (const id of dto.symbols) {
       const symbol = byId.get(id)
       if (symbol) symbols.push(symbol)
       else unresolved.push(id)
     }
     return mapWatchlistDto(dto, symbols)
   })
   return { watchlists, unresolved }
   ```
   (Callers currently expect `Watchlist[]`; add a compatibility wrapper or update call sites.)
2. In `WatchlistRoot.tsx`, `loadCanonicalWatchlists` should now return the `{watchlists, unresolved}` shape; if `unresolved.length > 0`, call `useToast().showToast('Some symbols could not be loaded and were hidden')` (or use a store field for a persistent banner).
3. Keep `SymbolResolveError` for the "everything failed for a whole list" case — surface only when a watchlist has ≥ 1 symbol and ends up with 0 resolved.
4. Update `resolveWatchlistDtos` tests: previously-throw cases now assert partial results.

---

### FE-L2-011: `resolveReplayWsUrl` appends JWT to any absolute `ws(s)://` URL
Severity: Minor | Effort: S | Rank: 26

`resolveReplayWsUrl` (`replayWsClient.ts:30-37`) early-returns `appendToken(wsUrl)` when the string starts with `ws://` / `wss://` — so a BE `ws_url` value pointing at an arbitrary host would still get the JWT appended. Theoretical today; latent footgun.

#### Solution 1: Reject absolute URLs (accept relative paths only, build the origin locally)
- Approach: Remove the `startsWith('ws://')` / `startsWith('wss://')` branch. If a caller passes an absolute URL, either log a `console.warn` and strip everything except the pathname+query, or throw `new Error('Replay ws_url must be relative')`. Always construct the WS URL from `location` and the relative path.
- Pros/Cons:
  - + Zero exposure to third-party hosts.
  - + Matches BE current behavior — `POST /replay/sessions` returns `/ws/replay/{id}` (`backend/api/routers/replay.py:39-43`) — nothing legitimately relies on absolute URLs.
  - − If a future BE ever needs to point clients at a different host (e.g. dedicated WS gateway), the FE has to be updated.
- Files likely touched: `frontend/src/services/replayWsClient.ts`, `frontend/src/services/replayWsClient.test.ts`.

#### Solution 2: Same-origin allowlist assertion
- Approach: Keep the absolute-URL branch, but before `appendToken`, assert `new URL(wsUrl).host === location.host`. If mismatch, refuse to append the token (return the URL unmodified, or throw).
- Pros/Cons:
  - + Allows future absolute URLs from the same host without a FE change.
  - + Same defense-in-depth as Solution 1 for cross-origin cases.
  - − Slightly more code (URL parsing, error path).
  - − Same-origin comparison via `URL.host` handles port correctly but subdomain gateways (`ws.example.com` vs `example.com`) require explicit rules.
- Files likely touched: same as Solution 1.

#### Recommended: Solution 2
Justification: Solution 2 is only marginally more code but keeps the door open for a same-origin WS gateway path. The core protection (JWT never leaves same-origin) is what Agent B flagged. Also, if FE-L2-003 lands (`?ticket=` instead of `token=`), Solution 2's `appendTicket` variant still needs the same host check.

Implementation notes for Agent H:
1. In `resolveReplayWsUrl`, replace the current `startsWith('ws://')` branch with:
   ```ts
   if (wsUrl.startsWith('ws://') || wsUrl.startsWith('wss://')) {
     const parsed = new URL(wsUrl)
     if (parsed.host !== location.host) {
       throw new Error(`Refusing to open replay WS on foreign host: ${parsed.host}`)
     }
     return appendToken(wsUrl)
   }
   ```
2. Apply the same guard in `liveWsClient.ts`'s `resolveLiveWsUrl` (currently reads from `VITE_LIVE_WS_URL`) — if `configured` is absolute, assert it matches `location.host` before appending the token/ticket.
3. Test: extend `replayWsClient.test.ts` with a `wss://evil.example.com/x` case → asserts throw.
4. If Solution 1 is preferred by reviewers (stricter), invert to "reject absolute" — the code shape is 3 lines shorter.

---

## Return-to-parent table

| Issue ID   | Recommended solution                                                       |
|------------|-----------------------------------------------------------------------------|
| FE-L2-001  | Read `row.bar`, drop phantom `incomplete` gate                             |
| FE-L2-002  | Adopt replay-style `onClose({code, reason, kind})` + shared `wsCloseCode` helper |
| FE-L2-003  | In-memory JWT + short-lived one-shot WS ticket (`POST /ws/tickets`)         |
| FE-L2-004  | Shared password-policy constants + mode-driven `minLength`                  |
| FE-L2-005  | Rewrite `ScanRequest`/`ScanResponse` to match `ScanCreateRequest`/`ScanRunResponse` |
| FE-L2-006  | Rewrite `AiClarifyRequest`/`AiExplainRequest` to match `ClarifyRequest`/`ExplainRequest` (+ typed translate union) |
| FE-L2-007  | Add `REPLAY_CLOSE_LIMIT = 4429` + `rate_limited` close-kind branch          |
| FE-L2-008  | `useReplayWs.onUnauthorized` callback wired in `useReplaySession` to reset store + strip URL |
| FE-L2-009  | Remove duplicate `clearLocalUserId` on 401 branch of `WatchlistRoot`; preserve `expired` reason |
| FE-L2-010  | Partial-resolve `resolveWatchlistDtos` — drop unresolved IDs, soft warning  |
| FE-L2-011  | Same-origin assertion in `resolveReplayWsUrl` (and `resolveLiveWsUrl`)      |
