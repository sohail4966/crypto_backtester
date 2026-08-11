# Agent D Report — BE Phase 11: Auth core

| Field | Value |
|---|---|
| **Agent** | D |
| **Status** | Complete |
| **Scope** | Migration V010, auth module, user repo/queries, auth router/service, protect users/watchlists |

## Delivered

- `V010__user_password_hash.sql` — nullable `password_hash`
- `api/auth.py` — bcrypt + PyJWT HS256
- `api/routers/auth.py` + `services/auth_service.py` + `schemas/auth.py`
- User repository email lookup + claim update
- Watchlist + user mutation routes require JWT ownership
- `GET /users` list requires JWT; `GET /users/{id}` + `POST /users` public
- Deps: `PyJWT`, `bcrypt` in `requirements.txt`
- Settings: `JWT_SECRET`, `JWT_EXPIRE_MINUTES`, `LIVE_WS_POLL_INTERVAL_MS`

## Notes

- Phase 10 `/ai` router left mounted and public.
- Replay V007 left unchanged (verified complete).
