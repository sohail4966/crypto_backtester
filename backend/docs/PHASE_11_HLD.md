# Phase 11 High Level Design — Auth + Live WS (Backend slice)

**Status:** Backend auth + live complete — see [Completion Assessment](#phase-11-completion-assessment)  
**Prerequisite:** Phase 4 API, Phase 4c replay DB (D-93 / V007), existing FE chart client  
**Decisions:** D-115 (JWT + password_hash), D-116 (DB-tail live WS), D-117 (replay verified)  
**Agent artifacts:** [docs/agents/be-phase-11-auth-live/](../../docs/agents/be-phase-11-auth-live/)  
**Note:** ROADMAP Phase 11 also covers broader Web UI; this HLD covers the **backend gaps**
from D-78 plus minimal FE token wiring. FE chart UI remains partial.

---

## Starting Point

Phase 4 shipped a public API (D-69). Auth, live candle WS, and replay DB were deferred
(D-78). Phase 4c already persisted `app.replay_sessions` (D-93). Frontend SPA exists and
bootstraps a local user without passwords.

**Phase 11 backend goal:** JWT ownership for user-scoped data + live closed-candle WS.

---

## Done Criteria

1. `password_hash` on `app.users` (nullable legacy).
2. `/auth/register`, `/auth/login`, `/auth/claim` issue JWTs.
3. Watchlist routes + user PATCH/DELETE require matching JWT `sub`.
4. Public matrix documented (health, catalog, candles, chart-data, indicators, scan,
   backtest, replay, live WS, `/ai/*`).
5. `WS /ws/live` DB-tail of latest closed bars.
6. Replay V007 verified — no duplicate table.
7. OpenAPI + pytest green; minimal FE Authorization header.
8. Do not delete Phase 10 `/ai` routes.

---

## Architecture

```
POST /auth/* ──► bcrypt + JWT
Watchlists ───► Bearer JWT (sub == user_id)
WS /ws/live ──► poll CandleService.get_latest_candles → candle events
/ai/* ────────► unchanged mount (public v1)
Replay ───────► V007 checkpoint (unchanged)
```

### Route matrix

| Surface | Auth |
|---|---|
| Meta, symbols, candles, chart-data, indicators | Public |
| Scan, backtest, replay REST + `/ws/replay` | Public |
| `/ws/live` | Public |
| `/auth/register|login|claim` | Public |
| `POST /users`, `GET /users/{id}` | Public |
| `GET /users` list | JWT |
| User PATCH/DELETE | JWT + ownership |
| All watchlist routes | JWT + ownership |
| `/ai/*` | Public (optional JWT later) |

---

## Live WS

- Path: `/ws/live`
- Client: `subscribe` / `unsubscribe` / `ping`
- Server: `subscribed` / `candle` / `pong` / `error`
- Source: DB latest closed candle (not exchange stream)
- Env: `LIVE_WS_POLL_INTERVAL_MS` (default 2000)

---

## Replay gap check

| Item | Status |
|---|---|
| `V007__replay_sessions.sql` | Present |
| Checkpoint + reconnect rebuild | Present (Phase 4c) |
| Phase 11 action | Verified complete (D-117) |

---

## Phase 11 Completion Assessment

**Backend auth + live:** Complete for D-78 remainder.

| Area | Score | Notes |
|---|---|---|
| JWT auth | 9/10 | register/login/claim + ownership |
| Live WS | 8/10 | DB-tail pragmatic; no exchange stream |
| Replay persistence | 9/10 | Already shipped in 4c |
| OpenAPI / tests | 9/10 | auth + live covered |
| FE login UI | n/a | Minimal token wiring only |

**Residual:** Polished login UI, exchange live feeds, JWT on `/ai` and live WS if needed.

**Completion:** Backend slice **100%** of auth+live scope; overall Phase 11 Web UI **partial**.
