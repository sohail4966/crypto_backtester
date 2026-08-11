# Multi-Agent Pipeline Queue

**Mode:** No human-in-loop. Per feature: Agents A → H; artifacts under `docs/agents/<feature>/`.

## All phases complete

| Feature | Path | Verdict |
|---|---|---|
| FE Phase 3 — Replay | `fe-phase-3-replay/` | READY_WITH_NITS |
| FE Phase 4 — Watchlist | `fe-phase-4-watchlist/` | READY_WITH_NITS |
| FE Phase 5 — Drawings | `fe-phase-5-drawings/` | READY_WITH_NITS |
| BE Phase 4d — Backtest HTTP | `be-phase-4d-backtest-api/` | READY_WITH_NITS |
| FE Phase 6 — Multi-Chart | `fe-phase-6-multi-chart/` | READY_WITH_NITS |
| BE Phase 5 — Market Structure | `be-phase-5-structure/` | READY_WITH_NITS |
| BE Phase 6 — Patterns | `be-phase-6-patterns/` | READY_WITH_NITS |
| BE Phase 7 — SMC | `be-phase-7-smc/` | READY_WITH_NITS |
| BE Phase 8 — Screener | `be-phase-8-screener/` | READY_WITH_NITS |
| BE Phase 9 — DSL | `be-phase-9-dsl/` | READY_WITH_NITS |
| BE Phase 10 — AI NL | `be-phase-10-ai/` | READY_WITH_NITS |
| BE Phase 11 — Auth + Live WS | `be-phase-11-auth-live/` | READY_WITH_NITS (ROADMAP: Partial — FE login UI not overhauled) |
| Full-stack hardening (A→H loop) | `full-stack-hardening/` | **READY** (G3: NONE remaining) |
| Full-stack hardening Loop 2 (A→H) | `full-stack-hardening/LOOP2_*` | **READY** (G Loop2: NONE remaining — 31 issues fixed) |

## Frontend roadmap

Phases 0–6: **Complete (v1)**

## Backend roadmap

Phases 0–10: **Complete** · Phase 11: **Complete** (auth+live hardened; FE AuthGate + `/auth/me` in full-stack hardening)
