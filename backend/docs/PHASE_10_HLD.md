# Phase 10 High Level Design — AI Natural Language Interface

**Status:** Complete — see [Phase 10 Completion Assessment](#phase-10-completion-assessment)  
**Prerequisite:** Phase 9 Trading DSL (`validate_strategy`, `strategy_json_schema`)  
**Decisions:** D-112 (pluggable LLM), D-113 (ask-on-ambiguity), D-114 (schema-in-prompt + validate gate)  
**Agent artifacts:** [docs/agents/be-phase-10-ai/](../../docs/agents/be-phase-10-ai/)  
**Parallel note:** Phase 11 owns auth/JWT. Phase 10 routes stay public under `/api/v1/ai`
(may be wrapped later without changing AI package contracts).

---

## Starting Point

Phase 9 shipped a versioned DSL with pydantic models and JSON Schema export for LLM
prompts. Traders still need plain-English → validated strategy JSON without the model
generating or executing code.

**Phase 10 goal:** NL → DSL translation layer with clarification loop and optional
explain-back.

---

## Done Criteria

1. Pluggable LLM provider (`mock` + OpenAI-compatible HTTP).
2. System prompt injects Phase 9 JSON Schema + few-shots.
3. LLM output validated via `dsl.validate_strategy` before return.
4. Ambiguous input → clarification questions (ask-on-ambiguity).
5. Clarify endpoint completes the loop with session answers.
6. Explain-back (template) for a valid strategy.
7. REST `POST /api/v1/ai/translate|clarify|explain` (public).
8. API key from env only; mock tests offline in CI.
9. ROADMAP Phase 10 complete; A–H artifacts; OQ-26–28 resolved.

---

## Architecture

```
ai/
  providers/
    base.py              LLMProvider protocol
    mock.py              offline fixtures
    openai_compat.py     httpx chat completions
  prompt.py              schema + few-shots system prompt
  translate.py           parse envelope → validate
  explain.py             template English
  sessions.py            in-memory clarification store
  types.py               shared dataclasses

api/routers/ai.py        /ai/* HTTP
api/services/ai_service.py
api/schemas/ai.py
```

### Data flow (translate)

1. Client sends NL text.
2. Build system prompt (`strategy_json_schema()` + examples + available indicators).
3. Provider returns JSON envelope (`ok` | `needs_clarification`).
4. If clarification: store session, return questions + `session_id`.
5. If ok: `validate_strategy`; on success return strategy (+ template explanation).
6. Invalid JSON/DSL → 422; live provider HTTP errors → 502.

---

## Key principle

The LLM generates **data (JSON)**, not code. The backtest engine remains deterministic.
Clients pass the returned strategy to `/backtest` (Phase 4d) separately.

---

## Environment

| Variable | Default | Notes |
|---|---|---|
| `AI_LLM_PROVIDER` | auto | `mock` \| `openai_compat` |
| `AI_LLM_API_KEY` | — | Required for live provider |
| `AI_LLM_BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible |
| `AI_LLM_MODEL` | `gpt-4o-mini` | |
| `AI_LLM_TIMEOUT_SEC` | `60` | |
| `AI_CLARIFY_TTL_MINUTES` | `30` | Session TTL |

---

## Phase 10 Completion Assessment

| Criterion | Status | Evidence |
|---|---|---|
| Pluggable providers | **PASS** | `ai/providers/*`, `test_providers.py` |
| Schema-in-prompt | **PASS** | `ai/prompt.py`, `test_prompt.py` |
| Validate gate | **PASS** | `translate.py` + `INVALID_DSL` tests |
| Clarification loop | **PASS** | `sessions.py`, translate/clarify API tests |
| Explain template | **PASS** | `explain.py`, `POST /ai/explain` |
| REST `/ai/*` | **PASS** | `api/routers/ai.py` |
| Env secrets | **PASS** | `.env.example` placeholders only |
| Offline CI tests | **PASS** | `pytest tests/ai/ tests/api/test_ai.py` → 19 passed |
| Docs + OQ-26–28 | **PASS** | D-112–D-114; ROADMAP Complete |

**Verdict:** Complete for translation + clarify + explain scope. Deferred: backtest
narrative, strategy suggestions, LLM-powered explain, DB-backed sessions.
