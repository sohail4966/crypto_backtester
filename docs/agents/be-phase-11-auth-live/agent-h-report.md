# Agent H Report — BE Phase 11: Auth + Live WS (Final E2E Review)

| Field | Value |
|---|---|
| **Verdict** | **READY_WITH_NITS** |
| **Date** | 2026-08-11 |
| **Inputs** | [prd.md](./prd.md), [tech-design.md](./tech-design.md), [answers.md](./answers.md), D–G reports |
| **Quality gate** | `pytest tests/api/` green; PHASE_11_HLD + ROADMAP partial; D-115–D-117 |

---

## Final verdict

**READY_WITH_NITS** — Backend Phase 11 ships JWT auth wrapping `app.users`
(register/login/claim), ownership-protected watchlists, and `WS /ws/live` DB-tail
of latest closed candles. Replay persistence was already complete in Phase 4c
(V007 / D-93) and verified (D-117). Phase 10 `/ai` routes remain mounted. Minimal
FE attaches `Authorization` when a token is present. Overall ROADMAP Phase 11 is
**Partial** (FE chart UI already exists; backend auth+live complete).

---

## AC checklist

| AC | Criterion | Status | Evidence |
|---|---|---|---|
| **AC-1** | Register → JWT | **PASS** | `test_register_returns_jwt` |
| **AC-2** | Login / bad creds | **PASS** | `test_login_ok_and_bad_password` |
| **AC-3** | Claim once | **PASS** | `test_claim_sets_password_once` |
| **AC-4** | Watchlist JWT ownership | **PASS** | `test_watchlist_requires_matching_jwt` |
| **AC-5** | Public catalog/health | **PASS** | `test_health_stays_public`; matrix in HLD/OpenAPI |
| **AC-6** | Live WS candle push | **PASS** | `test_live_ws_subscribe_pushes_candle` |
| **AC-7** | Replay DB verified | **PASS** | V007 + D-117; no new table |
| **AC-8** | OpenAPI auth + live | **PASS** | `openapi.yaml` auth paths + `x-websocket.live` |
| **AC-9** | Pytest | **PASS** | 77 passed (`tests/api/`) |
| **AC-10** | FE Authorization | **PASS** | `api.ts` + bootstrap claim/register |
| **AC-11** | Docs; no `/ai` deletion | **PASS** | PHASE_11_HLD; `ai.router` still mounted |

---

## Test results

```
pytest tests/api/ -q
→ 77 passed in ~4.6s

vitest src/services/userBootstrap.test.ts
→ 7 passed
```

---

## Docs status updates

| Doc | Change |
|---|---|
| `backend/docs/PHASE_11_HLD.md` | Created + completion assessment |
| `backend/docs/ROADMAP.md` | Phase 11 → **Partial** (backend auth+live complete) |
| `backend/docs/DECISIONS.md` | D-115, D-116, D-117 |
| `backend/docs/OPEN_QUESTIONS.md` | OQ-52/53/58 Phase 11 notes |
| `backend/docs/openapi.yaml` | Auth + live WS + bearerAuth |
| `docs/agents/PIPELINE_QUEUE.md` | Mark `be-phase-11-auth-live` done |
| `docs/agents/be-phase-11-auth-live/*` | A–H artifacts |

---

## Residual risks / nits

1. Live WS is DB-tail only — latency follows sync/poll interval, not exchange tick.
2. `/ai/*` and live WS remain public; tighten later if needed.
3. No polished login UI — DEV password claim path for SPA bootstrap.
4. `JWT_SECRET` local default must be overridden outside localhost.
5. OpenAPI does not annotate every watchlist mutation with `security:` (list/create do; others rely on description matrix).

---

## Completion notes

Use `Authorization: Bearer <token>` from `/auth/register|login|claim`. Connect
`WS /ws/live` and `subscribe` with symbols + timeframe for closed-candle tails.
