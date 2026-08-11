# Tech Design — BE Phase 10: AI Natural Language Interface

| Field | Value |
|---|---|
| **Status** | Ready for implementation (Agent B answers incorporated) |
| **PRD** | [prd.md](./prd.md) (Approved) |
| **Decisions** | D-112, D-113, D-114 |
| **HLD** | [PHASE_10_HLD.md](../../../backend/docs/PHASE_10_HLD.md) |
| **Agent D** | `ai/` package (providers, prompt, translate, explain, sessions) |
| **Agent E** | REST `/api/v1/ai/*` |
| **Answers** | [answers.md](./answers.md) |

---

## 1. Architecture Overview

```
Client
  │  POST /api/v1/ai/translate | clarify | explain
  ▼
┌─────────────────────┐
│ api.routers.ai      │  pydantic request/response
│ api.services.ai_*   │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ ai.translate        │  build prompt → provider.complete → parse → validate
│ ai.explain          │  template walk (no LLM)
│ ai.sessions         │  in-memory clarification state
└──────────┬──────────┘
           ▼
┌─────────────────────┐     ┌──────────────────┐
│ ai.providers.*      │     │ dsl.validate_*   │
│ mock | openai_compat│────►│ strategy_json_   │
└─────────────────────┘     │ schema()         │
                            └──────────────────┘
```

### Responsibilities

| Layer | Owns | Does not own |
|---|---|---|
| **`ai/`** | Prompting, providers, parse/validate gate, clarify sessions, explain | Backtest execution, auth, DB |
| **`api/` AI routes** | HTTP schemas + error mapping | Prompt text |
| **`dsl/`** | Schema + validation (import only) | NL |

---

## 2. Package layout

```
backend/
  ai/
    __init__.py
    types.py              # envelopes, ClarificationQuestion, TranslateOutcome
    prompt.py             # system prompt + few-shots + schema injection
    providers/
      __init__.py         # get_provider()
      base.py             # Protocol LLMProvider
      mock.py             # fixture responses (offline)
      openai_compat.py    # httpx chat completions
    sessions.py           # in-memory ClarificationSessionStore
    translate.py          # translate_nl / apply_clarification
    explain.py            # explain_strategy template
  api/
    routers/ai.py
    schemas/ai.py
    services/ai_service.py
    settings.py           # + AI_LLM_* helpers
  tests/ai/
    test_prompt.py
    test_translate.py
    test_explain.py
    test_providers.py
  tests/api/test_ai.py
  docs/PHASE_10_HLD.md
```

### Do not modify

- Phase 11 auth / JWT files (if present)
- `screener/`, `patterns/`, `smc/` bodies
- DSL grammar (import only)

---

## 3. LLM response envelope

```json
{
  "status": "ok",
  "strategy": {
    "schema_version": "1",
    "entry": { "...": "..." },
    "exit": { "...": "..." }
  }
}
```

or

```json
{
  "status": "needs_clarification",
  "questions": [
    {
      "id": "rsi_oversold",
      "prompt": "What RSI level should count as oversold?",
      "options": ["30", "25", "20"]
    }
  ]
}
```

After `status=ok`, call `validate_strategy(strategy)`. Failure → `INVALID_DSL` 422.

---

## 4. HTTP API

### `POST /api/v1/ai/translate`

```json
{ "text": "buy when daily RSI is oversold and price above 200 SMA" }
```

Responses:

- `200` `{ "status": "ok", "strategy": {...}, "explanation": "..." }`
- `200` `{ "status": "needs_clarification", "session_id": "...", "questions": [...] }`
- `422` validation / empty text / invalid DSL from model

### `POST /api/v1/ai/clarify`

```json
{
  "session_id": "uuid",
  "answers": { "rsi_oversold": "30" }
}
```

Same response union as translate. Unknown/expired session → `404 SESSION_NOT_FOUND`.

### `POST /api/v1/ai/explain`

```json
{ "strategy": { "entry": {...}, "exit": {...} } }
```

→ `{ "explanation": "..." }` after validate.

---

## 5. Environment

| Variable | Default | Purpose |
|---|---|---|
| `AI_LLM_PROVIDER` | auto | `mock` \| `openai_compat` |
| `AI_LLM_API_KEY` | unset | Bearer token (never commit) |
| `AI_LLM_BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible base |
| `AI_LLM_MODEL` | `gpt-4o-mini` | Model id |
| `AI_LLM_TIMEOUT_SEC` | `60` | HTTP timeout |
| `AI_CLARIFY_TTL_MINUTES` | `30` | Session idle TTL |

---

## 6. Mock provider fixtures

| Trigger in user text | Behavior |
|---|---|
| contains `AMBIGUOUS:` or phrase `RSI is low` (no number) | `needs_clarification` |
| contains `INVALID:` | returns strategy missing required fields |
| default / `RSI` + `SMA` style | valid RSI + SMA mean-reversion strategy |

---

## 7. Testing

- Unit: prompt contains schema keys; mock translate paths; explain template; validate gate.
- API: TestClient with mock provider forced via env / monkeypatch — **no network**.
- Do not call real LLM in CI.

---

## 8. Error codes

| Code | HTTP | When |
|---|---|---|
| `EMPTY_TEXT` | 422 | Blank translate text |
| `INVALID_LLM_JSON` | 422 | Provider returned non-JSON / bad envelope |
| `INVALID_DSL` | 422 | Strategy failed `validate_strategy` |
| `SESSION_NOT_FOUND` | 404 | Unknown/expired clarify session |
| `PROVIDER_ERROR` | 502 | Upstream HTTP failure (live provider only) |
