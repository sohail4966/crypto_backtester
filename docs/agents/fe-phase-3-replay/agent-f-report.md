# Agent F Report — FE Phase 3: Replay (Backend Review)

| Field | Value |
|---|---|
| **Verdict** | **Approve** — Agent D no-op is correct; no backend fix applied |
| **Date** | 2026-08-11 |
| **Reviewed** | [agent-d-report.md](./agent-d-report.md) vs [tech-design.md](./tech-design.md) §2–3, §8 |
| **Code changes** | None |

---

## Verdict

Agent D’s conclusion stands: Phase 4c already provides the migration, REST, and WS v2 contract Agent E needs. Spot-checks of live code match the tech design. **No hard protocol blocker** was found. No backend / migration edits were made.

---

## Spot-check results

### Database

| Claim (Agent D) | Verified |
|---|---|
| `V007__replay_sessions.sql` present | Yes — `backend/data/migrations/sql/V007__replay_sessions.sql` |
| Columns: session_id, symbol FK, timeframe, step_timeframe, start_anchor, cursor_ts, indicators JSONB, speed, state, created_at, updated_at | Yes |
| Index on `updated_at` | Yes — `idx_replay_sessions_updated_at` |
| New FE Phase 3 migrations | None required (tech-design §2) |

### REST

| Method | Path | Verified |
|---|---|---|
| `POST` | `/api/v1/replay/sessions` → `201` `ReplaySessionResponse` | `routers/replay.py` + `main.py` `include_router(..., prefix="/api/v1")` |
| `GET` | `/api/v1/replay/sessions/{session_id}` → `ReplayStateResponse` | Same |
| `DELETE` | `/api/v1/replay/sessions/{session_id}` → `204` | Same |

Create response is snake-only (`session_id`, `ws_url`) with relative `ws_url` `/ws/replay/{uuid}` — matches Agent D notes and tech-design §6.1.

### WebSocket

| Check | Verified |
|---|---|
| Path `WS /ws/replay/{session_id}` | `@router.websocket` in `api/ws/replay.py`; mounted at app root (no `/api/v1`) |
| Client actions | `play`, `pause`, `step`, `seek`, `set_speed`, `refill`, `set_indicators`, `get_state` |
| Server events | `replay_state`, `snapshot`, `tick_batch`, `buffer_loading`, `buffer_ready`, `buffer_reset`, `replay_completed`, `error` |
| Close `4404` | `WS_REPLAY_NOT_FOUND` before accept on unknown session |
| Close `4401` | Prior tab superseded (last-connection-wins) |
| Connect handshake | `replay_state` then `snapshot` (then optional autoplay batch) |

Supporting tests exist under `backend/tests/api/test_replay_*.py` (not re-run as a gate for this review).

### Contract quirks Agent D flagged (FE, not backend)

| Quirk | Live-code confirmation |
|---|---|
| Mixed snake/camel on `replay_state` | `model_dump(by_alias=True)` — aliases on `startAnchor` / `latestAvailable` / `barIndex` / `queueRemaining`; unaliased snake for `session_id`, `step_timeframe`, `cursor`, `state`, `speed` |
| Fresh cursor one bar before anchor | `shift_unix_by_bars(start_anchor, …, 1)` moves earlier; `snapshot_bars()` returns `[]` when cursor precedes window |
| `step` without `count` | Defaults to full `replay_tick_batch_size()` — FE must send `count: 1` |
| `set_indicators` may restore playing | After `buffer_reset` + `snapshot` + `replay_state`, if prior was playing, engine state flipped to `playing` without a new batch — FE must pause + send `{ action: "pause" }` |

These are adapter/UX concerns already assigned to Agent E in the tech design. They do **not** justify Agent D work.

---

## Findings

1. **No-op approved.** Agent D’s checklist is accurate; paths and mounts match.
2. **No missed blocker.** Required REST/WS surfaces, V007, and close codes are present and wired.
3. **No fix applied.** Backend tree unchanged for this phase (review is documentation-only).

---

## Residual risks (for Agent E / QA)

| Risk | Owner |
|---|---|
| FE normalize must accept both casings on every aliased field | Agent E |
| Omitting `step.count` advances a full batch | Agent E (`count: 1` always) |
| `set_indicators` playing flip without batch | Agent E (force pause + WS `pause`) |
| OpenAPI casing may lag live code | Agent E — prefer live FastAPI/WS |
| Known polish (`buffer_loading` mid-batch, `SUPERSEDED` untested in FE) | FE timeouts / amber UX — not Agent D |
| Live smoke against local Phase 4c still required before claiming E2E | Agent E / QA |

---

## Artifacts

| Item | Status |
|---|---|
| Backend / DB code changes | **None** |
| This report | `docs/agents/fe-phase-3-replay/agent-f-report.md` |
| Next | **Agent E** — frontend implementation per tech-design §8 |
