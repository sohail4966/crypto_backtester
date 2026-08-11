# Tech Design — BE Phase 11: Auth + Live WS

| Field | Value |
|---|---|
| **Status** | Ready for implementation (Agent B answers incorporated) |
| **PRD** | [prd.md](./prd.md) (Approved) |
| **Decisions** | D-115 (JWT + password_hash), D-116 (DB-tail live WS), D-117 (public route matrix) |
| **HLD** | [PHASE_11_HLD.md](../../../backend/docs/PHASE_11_HLD.md) |
| **Answers** | [answers.md](./answers.md) |

---

## 1. Architecture Overview

```
SPA (minimal)                    FastAPI
─────────────                    ───────
localStorage token ──Bearer──►  deps.get_current_user
register/login/claim ─────────► auth_service (bcrypt + JWT)
watchlist CRUD ───────────────► require ownership (sub == user_id)
WS /ws/live ◄── candle ─────── live poll loop → CandleService / repository
WS /ws/replay (unchanged) ──── replay_sessions V007 checkpoint
```

### Responsibilities

| Layer | Owns | Does not own |
|---|---|---|
| **`api/auth*`** | Hash, JWT issue/verify, register/login/claim | Watchlist business logic |
| **`deps`** | `get_current_user`, ownership helpers | Password policy UI |
| **`ws/live`** | Subscribe set, poll, push on change | Exchange feeds |
| **Replay** | Existing V007 path (verify only) | New persistence design |
| **FE api.ts** | Attach Authorization if token | Login page |

---

## 2. Package / file layout

```
backend/
  data/migrations/sql/V010__user_password_hash.sql
  api/
    auth.py                 # JWT encode/decode, password hash verify
    deps.py                 # + get_current_user, require_user_id match
    settings.py             # JWT_* , LIVE_WS_POLL_INTERVAL_MS
    routers/auth.py
    schemas/auth.py
    services/auth_service.py
    repositories/user_repository.py  # password_hash fields + get_by_email
    repositories/queries.py
    ws/live.py
    main.py                 # mount auth + live WS
  tests/api/test_auth.py
  tests/api/test_live_ws.py
  docs/PHASE_11_HLD.md
  docs/openapi.yaml
frontend/
  src/constants/auth.ts     # AUTH_TOKEN_STORAGE_KEY, DEV_PASSWORD
  src/services/api.ts       # Authorization header
  src/services/authToken.ts
  src/services/userBootstrap.ts  # claim/register after ensure
```

### Do not modify

- Phase 10 `/ai` routers if/when present (mounts stay).
- Replay WS protocol v2 semantics.
- Exchange loader / sync pipeline (live WS only reads DB).

---

## 3. Auth details

### Migration

```sql
ALTER TABLE app.users ADD COLUMN IF NOT EXISTS password_hash TEXT;
```

### JWT payload

```json
{ "sub": "<user_uuid>", "email": "...", "exp": ... }
```

### Route matrix

| Surface | Auth |
|---|---|
| `GET /health`, meta, symbols, candles, chart-data, indicators | Public |
| scan, backtest, replay REST + `/ws/replay` | Public |
| `/ws/live` | Public (v1) |
| `POST /auth/register|login|claim` | Public |
| `POST /users` | Public (passwordless; legacy) |
| `GET /users/{id}` | Public |
| `GET /users` (list) | JWT required |
| User PATCH/DELETE | JWT + `sub == user_id` |
| All `/users/{user_id}/watchlists*` | JWT + `sub == user_id` |

### Errors

- Missing/invalid JWT → `401` `UNAUTHORIZED`
- Valid JWT wrong user → `403` `FORBIDDEN`
- Bad login → `401` `INVALID_CREDENTIALS`
- Claim when hash exists → `422` `PASSWORD_ALREADY_SET`

---

## 4. Live WS protocol

**Path:** `WS /ws/live`

**Client → server**

```json
{"action": "subscribe", "symbols": ["BTC/USDT"], "timeframe": "1m"}
{"action": "unsubscribe", "symbols": ["BTC/USDT"]}
{"action": "ping"}
```

**Server → client**

```json
{"type": "subscribed", "symbols": ["BTC/USDT"], "timeframe": "1m"}
{"type": "candle", "symbol": "BTC/USDT", "timeframe": "1m", "bar": {"time": 1, "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}}
{"type": "pong"}
{"type": "error", "code": "...", "message": "..."}
```

**Poll loop:** every `LIVE_WS_POLL_INTERVAL_MS`, for each subscribed (symbol, timeframe),
load latest closed bar; if `time` differs from last pushed, emit `candle`.

---

## 5. Replay gap check

| Item | Status |
|---|---|
| `V007__replay_sessions.sql` | Present |
| Repository + checkpoint | Present |
| Tests `test_replay_sessions_db.py` | Present |
| Phase 11 action | Document complete; no new migration |

---

## 6. Agent split

| Agent | Deliverable |
|---|---|
| **D** | Migration, auth module, user repo/queries, auth router/service, protect routes |
| **E** | Live WS + OpenAPI auth/live sections |
| **F** | Tests auth + live WS; fix regressions |
| **G** | Minimal FE token wiring + bootstrap claim; docs HLD/ROADMAP/DECISIONS |
| **H** | E2E review + pytest summary + verdict |

---

## 7. Dependencies

Add to `backend/requirements.txt`:

- `PyJWT>=2.8.0`
- `bcrypt>=4.0.0`
