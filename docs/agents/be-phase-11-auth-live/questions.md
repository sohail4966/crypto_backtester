# Clarifying Questions — BE Phase 11: Auth + Live WS

Review of [prd.md](./prd.md), ROADMAP Phase 11, D-69/D-78/D-93, `app.users`, replay V007,
and FE `apiRequest` / user bootstrap.

Questions only — no proposed answers.

---

## Auth model

### Q1 — Password column

**Question:** Add nullable `password_hash TEXT` to `app.users` via new migration, keeping
legacy passwordless rows valid until claim?

### Q2 — Token algorithm / library

**Question:** HS256 JWT via PyJWT + bcrypt hashes, secret from `JWT_SECRET` env?

### Q3 — Claim vs register

**Question:** Confirm three public endpoints: `register` (new user), `login` (existing
with hash), `claim` (legacy passwordless email sets password once)?

### Q4 — POST /users

**Question:** Keep passwordless `POST /users` for backward compatibility, or force all
creates through `/auth/register`?

### Q5 — Protected surface

**Question:** Protect watchlist **writes** (and user PATCH/DELETE) with JWT ownership;
keep GET watchlists public or also require ownership?

### Q6 — List users

**Question:** Keep `GET /users` public for FE email recovery, or lock it down now that
claim/login exist?

### Q7 — Future /ai routes

**Question:** If `/ai` routers appear, leave them mounted and apply optional JWT
dependency without deleting?

---

## Live WS

### Q8 — Transport source

**Question:** Confirm DB-tail poll of latest closed candle (not exchange WS) for v1?

### Q9 — Path / protocol

**Question:** `WS /ws/live` with subscribe message + server `candle` events on bar change?

### Q10 — Auth on live WS

**Question:** Leave live WS public in v1 (catalog ticks), or require `?token=` query JWT?

### Q11 — Poll interval

**Question:** Configurable poll interval (default ~2s) via env?

---

## Replay

### Q12 — V007 completeness

**Question:** Treat D-93 / V007 checkpoint persistence as complete for Phase 11 unless
tests reveal a gap (no second table)?

---

## Frontend

### Q13 — Minimal FE

**Question:** Only wire Authorization header + localStorage token; bootstrap may call
claim/register with DEV credentials — no login page?

### Q14 — Breaking watchlist tests

**Question:** Update FE/API tests to supply JWT after auth endpoints land?
