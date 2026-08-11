# Agent D Report — FE Phase 3: Replay (Database + Backend)

| Field | Value |
|---|---|
| **Verdict** | **No-op** — zero backend / migration code changes |
| **Date** | 2026-08-11 |
| **Inputs** | [tech-design.md](./tech-design.md) §2, §3, §8; [answers.md](./answers.md) Q1–Q2 |
| **Code changes** | None |

---

## Conclusion

Phase 4c already ships the full replay contract FE Phase 3 needs: `V007` table, REST create/get/delete, and WS v2 control plane. Live code matches the tech design. **No hard protocol blocker** was found. Agent E should consume live FastAPI + WS as source of truth and normalize mixed casing on the FE.

---

## Verification checklist

### Database — migration present

| Check | Result | Path |
|---|---|---|
| `V007__replay_sessions.sql` | Present | `backend/data/migrations/sql/V007__replay_sessions.sql` |
| Table `app.replay_sessions` | Columns: `session_id`, `symbol` (FK → `app.symbols`), `timeframe`, `step_timeframe`, `start_anchor`, `cursor_ts`, `indicators` JSONB, `speed`, `state`, `created_at`, `updated_at` | Same |
| Index on `updated_at` | Present | Same |
| New migrations for FE Phase 3 | **None required** (tech-design §2) | — |

### REST — mounted and implemented

| Method | Path | Handler | Mount |
|---|---|---|---|
| `POST` | `/api/v1/replay/sessions` | `create_replay_session` → `201` `ReplaySessionResponse` | `main.py` → `replay.router` @ `/api/v1` + prefix `/replay` |
| `GET` | `/api/v1/replay/sessions/{session_id}` | `get_replay_session` → `ReplayStateResponse` | Same |
| `DELETE` | `/api/v1/replay/sessions/{session_id}` | `delete_replay_session` → `204` | Same |

**Files checked:**

- `backend/api/routers/replay.py` — all three endpoints
- `backend/api/main.py` — `include_router(replay.router, prefix="/api/v1")`
- `backend/api/schemas/replay.py` — `ReplaySessionCreate`, `ReplaySessionResponse`, `ReplayStateResponse`
- `backend/api/services/replay_service.py`, `replay_session_store.py`, `replay_engine.py`, `replay_buffer.py`
- `backend/api/repositories/replay_repository.py` + SQL in `queries.py`
- `backend/docs/openapi.yaml` — `/api/v1/replay/sessions` (+ `{session_id}`) documented

### WebSocket — path and protocol

| Check | Result | Path |
|---|---|---|
| Route | `WS /ws/replay/{session_id}` | `backend/api/ws/replay.py` `@router.websocket` |
| Mount | Root (no `/api/v1` prefix) | `main.py` → `include_router(replay_ws.router)` |
| Close `4404` | Unknown session before accept | `WS_REPLAY_NOT_FOUND` |
| Close `4401` | Prior tab superseded | Last-connection-wins |

**Client → server actions present:** `play`, `pause`, `step`, `seek`, `set_speed`, `refill`, `set_indicators`, `get_state`.

**Server → client events present:** `replay_state`, `snapshot`, `tick_batch`, `buffer_loading`, `buffer_ready`, `buffer_reset`, `replay_completed`, `error`.

**Tests present (supporting evidence, not re-run as a gate for this no-op):**

- `backend/tests/api/test_replay_ws.py`
- `backend/tests/api/test_replay_sessions_db.py`
- `backend/tests/api/test_replay_service.py`
- `backend/tests/api/test_replay_engine.py`
- `backend/tests/api/test_replay_buffer.py`

---

## Hard-blocker assessment

| Candidate gap | Assessment |
|---|---|
| Missing REST/WS routes | **No** — all required surfaces exist and are wired in `main.py` |
| Missing migration | **No** — `V007` present |
| Protocol break requiring backend rename | **No** — mixed snake/camel is intentional FE normalize work (answers Q1–Q2) |
| Fresh empty snapshot / cursor-before-anchor | Documented FE behavior, not a backend bug |
| `step` default count = full batch if omitted | FE must send `count: 1` — adapter concern, not Agent D |
| `set_indicators` may restore `playing` | FE sends WS `pause` — adapter/UX, not Agent D |

**Decision:** No minimal backend fix. Agent D remains documentation-only.

---

## Contract notes for Agent E

Consume **live code** first (`schemas/replay.py`, `ws/replay.py`, engine payloads); OpenAPI second (casing may lag).

1. **Create `201` wire:** snake-only — `session_id`, `ws_url` (no aliases on `ReplaySessionResponse`). Normalize to `{ sessionId, wsUrl }`.
2. **Create body:** snake — `symbol`, `timeframe`, `start`, `indicators`, `speed`, `autoplay`; omit `step_timeframe` to default to timeframe. `symbol` = trading-pair string (`BTC/USDT`).
3. **WS `replay_state`:** `model_dump(by_alias=True)` → mixed camel aliases (`startAnchor`, `latestAvailable`, `barIndex`, `queueRemaining`) + unaliased snake (`session_id`, `step_timeframe`, `cursor`, `state`, `speed`). Accept both casings on GET and WS.
4. **Fresh session:** `cursor` is one bar before `start_anchor`; initial `snapshot.bars` is `[]`. First `step`/`play` tick reveals the anchor.
5. **Step:** Always send `{ "action": "step", "count": 1 }` — omitting `count` uses full server batch size.
6. **Seek:** In-window → `replay_state` only (`reloaded=false`); out-of-window → `buffer_reset` + `snapshot`. Slice trail locally on in-window.
7. **`set_indicators`:** Expect `buffer_reset` + `snapshot` + `replay_state`; if prior was playing, server may set `playing` again without a new batch — FE must force pause + send `{ "action": "pause" }`.
8. **Close codes:** `4404` unknown session; `4401` superseded. Map to amber connection UX.
9. **`ws_url`:** Relative path `/ws/replay/{uuid}` — build absolute via `location.host` + Vite `/ws` proxy.
10. **DELETE:** Best-effort teardown; treat `404` as success.

---

## Artifacts

| Item | Status |
|---|---|
| Backend / DB code changes | **None** |
| This report | `docs/agents/fe-phase-3-replay/agent-d-report.md` |
| Next agent | **Agent E** — full frontend implementation per tech-design §8 |
