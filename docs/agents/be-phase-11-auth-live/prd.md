# PRD — BE Phase 11: Auth + Live WS

| Field | Value |
|---|---|
| **Status** | Approved (auto — no human-in-loop; product defaults below) |
| **Phase** | Backend Phase 11 (auth + live gaps from ROADMAP / D-78) |
| **Product intent** | [ROADMAP.md — Phase 11](../../../backend/docs/ROADMAP.md#phase-11--visualization--web-ui) |
| **Prior contracts** | D-69 (no auth in Phase 4), D-77 (users name+email), D-78 (defer auth/live), D-93 (replay DB already in 4c) |
| **Agent artifacts** | `docs/agents/be-phase-11-auth-live/` |

---

## 1. Problem / Goal

### Problem

Phase 4 left the API fully public (D-69). Watchlists are spoofable via path
`user_id`. Live chart tail and JWT were deferred (D-78). Replay metadata persistence
already landed in Phase 4c (D-93 / V007) — Phase 11 must **verify**, not rebuild.

Frontend chart clients already exist; this phase ships **backend** auth + live WS,
with **minimal** FE wiring (Authorization header when a token is present).

### Goal

1. **JWT auth** wrapping `app.users` — register / login / claim-password for existing
   passwordless emails; bcrypt password hash; protect watchlist + user-scoped writes.
2. **Live candle WebSocket** — pragmatic DB-tail of latest closed bars for watchlist /
   chart tail (no exchange stream required in v1).
3. Confirm **replay session DB** gaps vs D-78/D-93; fill only if incomplete.
4. Update OpenAPI + tests; optional JWT on future `/ai` routes (do not delete Phase 10
   routes if present).
5. Minimal FE: attach `Authorization: Bearer <token>` when stored.

**Success:** Protected watchlist writes require matching JWT `sub`; public catalog /
health / historical chart routes remain readable; live WS pushes new closed candles
after sync; pytest green; ROADMAP marks backend auth+live complete (FE chart UI may
remain partial).

---

## 2. User Roles

| Role | Description | Auth |
|---|---|---|
| **Anonymous reader** | Health, symbols, candles, chart-data, indicators, scan, backtest, replay | None |
| **Authenticated user** | Own watchlist CRUD; own user patch/delete; optional live WS | JWT Bearer |
| **Dev SPA** | Bootstrap via register/claim + localStorage token | JWT |
| **QA** | `pytest tests/api/test_auth.py` + live WS tests | Local |

---

## 3. Scope

### In scope (v1)

- Migration: `password_hash` on `app.users` (nullable for legacy rows).
- `POST /api/v1/auth/register`, `/login`, `/claim` (set password on passwordless user).
- FastAPI deps: `get_current_user` / `require_user`; ownership checks on watchlists +
  user mutations.
- Document public vs protected route matrix in OpenAPI / HLD.
- `WS /ws/live` — subscribe symbols+timeframe; poll DB latest closed candle; push on change.
- Replay: verify V007 + checkpoint path; **no rebuild** unless a real gap is found.
- OpenAPI `x-websocket` live section; auth security scheme.
- Tests for auth + live WS.
- Minimal FE: token storage key + `apiRequest` Authorization header.
- `PHASE_11_HLD.md`, ROADMAP/DECISIONS/OPEN_QUESTIONS updates, A–H artifacts.

### Out of scope / deferred

| Item | Reason |
|---|---|
| Full login UI / password reset email | Minimal FE only |
| Exchange WebSocket ingest | Prefer DB-tail after sync |
| OAuth / refresh-token rotation | v1 HS256 access token sufficient |
| Multi-tenant admin roles | Single user ownership |
| Always-on cloud screener auth productization | Later |
| Deleting Phase 10 `/ai` routes | Must preserve if they exist |

---

## 4. Acceptance criteria

| ID | Criterion |
|---|---|
| **AC-1** | Register creates user + password hash + returns JWT |
| **AC-2** | Login returns JWT for correct password; 401 on bad creds |
| **AC-3** | Claim sets password on legacy passwordless email once; then login works |
| **AC-4** | Watchlist writes require JWT whose `sub` matches path `user_id` |
| **AC-5** | Health, symbols, candles, chart-data, indicators stay public (documented) |
| **AC-6** | Live WS pushes candle events when DB latest closed bar changes |
| **AC-7** | Replay DB persistence verified complete (or gaps filled) |
| **AC-8** | OpenAPI documents auth + live WS |
| **AC-9** | Pytest covers auth + live WS; existing API tests still pass (or updated) |
| **AC-10** | FE attaches Authorization when token present |
| **AC-11** | PHASE_11_HLD + ROADMAP status; A–H artifacts; no Phase 10 `/ai` deletion |

---

## 5. Non-goals

- Replacing replay WS protocol.
- Requiring JWT on historical chart reads in v1.
- Building a polished account settings UI.
