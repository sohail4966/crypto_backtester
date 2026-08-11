# Answers — BE Phase 11: Auth + Live WS (Agent B)

Decisive answers for [questions.md](./questions.md). Incorporated into
[tech-design.md](./tech-design.md) and [PHASE_11_HLD.md](../../../backend/docs/PHASE_11_HLD.md).

---

### Q1 → Answer

**Yes.** Migration `V010__user_password_hash.sql` adds nullable `password_hash TEXT`.
Legacy rows remain until `/auth/claim`. **D-115.**

### Q2 → Answer

**Yes.** PyJWT HS256 + bcrypt. `JWT_SECRET` (required in prod; local default allowed),
`JWT_EXPIRE_MINUTES` default 10080 (7d).

### Q3 → Answer

**Yes — three endpoints.**
- `POST /api/v1/auth/register` — name, email, password → user + default watchlist + JWT
- `POST /api/v1/auth/login` — email, password → JWT
- `POST /api/v1/auth/claim` — email, password — only if `password_hash IS NULL`; sets hash + JWT

### Q4 → Answer

**Keep `POST /users` passwordless** for backward compatibility and existing FE create path.
Prefer `/auth/register` for new clients. Watchlist writes still need JWT (claim after create).

### Q5 → Answer

**Protect all watchlist routes** (GET + mutations) and user PATCH/DELETE with JWT
`sub == user_id`. Anonymous cannot read/write another user’s watchlists.

### Q6 → Answer

**Require JWT for `GET /users` (list).** `GET /users/{id}` stays public so stored-id
validation still works without listing. Recovery uses claim/login by email.

### Q7 → Answer

**Yes.** Do not delete `/ai` routes. If present, optionally attach `get_current_user_optional`
or leave public until Phase 10 productizes — never remove mounts in this phase.

### Q8 → Answer

**Yes — DB-tail.** Poll latest closed candle via existing candle repository / service.
No exchange stream in v1.

### Q9 → Answer

**Yes.** `WS /ws/live`. Client: `subscribe` / `unsubscribe` / `ping`. Server:
`subscribed`, `candle`, `error`. Push only when latest bar `time` changes.

### Q10 → Answer

**Public live WS in v1** (same trust model as historical candles). Document that auth
can be added later via `?token=`.

### Q11 → Answer

**Yes.** `LIVE_WS_POLL_INTERVAL_MS` default `2000`.

### Q12 → Answer

**Yes — V007/D-93 is complete.** Phase 11 documents verification; no new replay table
unless a defect is found during implementation.

### Q13 → Answer

**Yes — minimal FE.** `AUTH_TOKEN_STORAGE_KEY`; `apiRequest` adds Bearer when present;
bootstrap claims/registers DEV user password and stores token. No login UI.

### Q14 → Answer

**Yes.** Update tests that hit protected routes to register/login/claim first.
