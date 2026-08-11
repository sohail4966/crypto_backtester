# PRD — BE Phase 10: AI Natural Language Interface

| Field | Value |
|---|---|
| **Status** | Approved (auto — no human-in-loop; product defaults below) |
| **Phase** | Backend Phase 10 |
| **Product intent** | [ROADMAP.md — Phase 10](../../../backend/docs/ROADMAP.md#phase-10--ai-natural-language-interface) |
| **Prior contracts** | Phase 9 `dsl/` (`validate_strategy`, `strategy_json_schema`), D-08 (JSON not code) |
| **Open questions resolved** | OQ-26, OQ-27, OQ-28 → D-112–D-114 |

---

## 1. Problem / Goal

### Problem

Traders can already express strategies as Phase 9 DSL JSON, but non-technical users
cannot author that grammar. An LLM translation layer is required so plain English
becomes a validated signal dict — without letting the model execute or generate code.

### Goal

Ship an **NL → DSL translation service** that:

1. Accepts free-text strategy descriptions.
2. Uses a **pluggable LLM provider** (OpenAI-compatible HTTP + offline mock).
3. Injects Phase 9 **JSON Schema** into the system prompt (OQ-28).
4. **Validates** LLM output with `dsl.validate_strategy` before returning.
5. **Asks clarifying questions** when input is ambiguous (OQ-27 default).
6. Optionally **explains** a DSL strategy back in plain English (template/stub OK).
7. Exposes public REST under `/api/v1/ai/*` (auth deferred to Phase 11).

Success: CI tests pass with the mock provider (no network); live provider is
env-configured and never commits secrets.

---

## 2. User Roles

| Role | Description | Auth |
|---|---|---|
| **Trader / FE client** | Describes strategies in English; answers clarifications. | Public (Phase 11 later) |
| **Developer / QA** | Runs `pytest tests/ai/ tests/api/test_ai.py` with mock provider. | Local |
| **Ops** | Sets `AI_LLM_*` env vars for a real OpenAI-compatible endpoint. | Env secrets |

---

## 3. Scope

### In scope (v1)

- Package `backend/ai/` — providers, prompt builder, translate + clarify + explain.
- REST: `POST /ai/translate`, `POST /ai/clarify`, `POST /ai/explain`.
- Pluggable providers: `mock` (fixtures) + `openai_compat` (HTTP chat completions).
- Validation gate via Phase 9 pydantic/JSON Schema.
- Clarification session store (in-memory) for the ask-on-ambiguity loop.
- Env-based API key / base URL / model; documented in `.env.example`.
- Tests with mock provider (no network).
- `PHASE_10_HLD.md`, ROADMAP update, D-112–D-114, OQ-26–28 resolved.
- A–H artifacts under `docs/agents/be-phase-10-ai/`.

### Out of scope / deferred

| Item | Reason |
|---|---|
| Backtest narrative / performance explanation | Stretch; not required for Done When core path |
| Strategy suggestions by asset/TF | Stretch; FE Phase later |
| JWT / auth on `/ai` | Phase 11 — keep routes public |
| Persistent clarification sessions (DB) | In-memory sufficient for v1 |
| Streaming chat UI | Frontend |
| Direct backtest execution from `/ai` | Client calls Phase 4d `/backtest` with returned DSL |

---

## 4. Acceptance criteria

| ID | Criterion |
|---|---|
| **AC-1** | NL text → validated DSL strategy via translate service |
| **AC-2** | LLM output rejected when it fails `validate_strategy` |
| **AC-3** | Ambiguous input returns clarification questions (not a guessed strategy) |
| **AC-4** | Clarify endpoint accepts answers and can complete translation |
| **AC-5** | Explain endpoint returns English for a valid strategy (template OK) |
| **AC-6** | Provider is pluggable (`mock` + `openai_compat`) |
| **AC-7** | JSON Schema from Phase 9 is included in the system prompt |
| **AC-8** | API key only from env; never committed |
| **AC-9** | REST under `/api/v1/ai/*`; no Phase 11 auth coupling |
| **AC-10** | `pytest tests/ai/ tests/api/test_ai.py` green offline |
| **AC-11** | PHASE_10_HLD + ROADMAP + A–H; OQ-26–28 resolved |

---

## 5. Product defaults (auto-resolved)

| Topic | Default |
|---|---|
| LLM choice (OQ-26) | **Pluggable** — OpenAI-compatible HTTP + mock fixture provider |
| Ambiguity (OQ-27) | **Ask clarifying questions** before emitting a strategy |
| Prompting (OQ-28) | Inject Phase 9 **JSON Schema** + few-shot examples; require JSON response |
| Default provider | `mock` when `AI_LLM_API_KEY` unset; `openai_compat` when set (or explicit `AI_LLM_PROVIDER`) |
| Explain | Deterministic template walk of the strategy tree |
| Auth | Public routes under `/ai` |

---

## 6. Non-goals reminder

The LLM generates **data (JSON)**, never code. The backtest engine stays fully
deterministic. AI is a translation / explanation layer only.
