# Answers — BE Phase 10: AI Natural Language Interface (Agent B)

Decisive answers for [questions.md](./questions.md). Incorporated into [tech-design.md](./tech-design.md)
and [PHASE_10_HLD.md](../../../backend/docs/PHASE_10_HLD.md).

---

### Q1 → Answer

**Providers return raw completion text** via `complete(system_prompt, user_prompt) -> str`.
The translate service owns JSON parse, envelope handling, and `validate_strategy`.

### Q2 → Answer

**Yes.** Default: `mock` if `AI_LLM_API_KEY` unset; `openai_compat` if set.
`AI_LLM_PROVIDER` (`mock` | `openai_compat`) always wins when present.

### Q3 → Answer

**Yes.** OpenAI-compatible `POST {AI_LLM_BASE_URL}/chat/completions` with Bearer key,
`AI_LLM_MODEL`, JSON object response format when requested, timeout from env.

### Q4 → Answer

**LLM-owned ambiguity** (prompted to emit `needs_clarification`). Mock fixtures
simulate both paths. No separate deterministic NL rules engine in v1.

### Q5 → Answer

**In-memory only** for clarification sessions. Optional idle TTL (default 30 min).
Process restart drops sessions — acceptable for v1.

### Q6 → Answer

**Yes.** `POST /ai/clarify` with `session_id` + `answers` map; service appends
Q&A to context and re-calls the provider; may return further questions or a strategy.

### Q7 → Answer

**Yes.** System prompt embeds `strategy_json_schema()` and documents the response
envelope. Model must not invent indicator names outside the known list when possible.

### Q8 → Answer

**HTTP 422** with code `INVALID_DSL` after parse/validate failure. No auto-retry in v1
(keeps CI deterministic). Clients may re-translate.

### Q9 → Answer

**Yes — include two few-shot examples** in the system prompt (RSI mean-reversion and
a multi-condition AND).

### Q10 → Answer

**Yes.** Public `/api/v1/ai/*`. Phase 11 may wrap later; do not add auth now.

### Q11 → Answer

**Yes — deterministic template explain** walking entry/exit trees. Optional LLM
explain can come later.

### Q12 → Answer

**Deferred.** Backtest narrative and strategy suggestions are out of Phase 10 v1.

### Q13 → Answer

**Separate endpoints** `translate` + `clarify` (+ `explain`). Clearer contracts for FE.

### Q14 → Answer

**Yes.** Do not fight Phase 11 auth files. Only add `ai/` package, AI router/schemas/
service, settings helpers, and `main.py` router include.

---

## Auto-resolved open questions

| OQ | Decision | Decision ID |
|---|---|---|
| OQ-26 | Pluggable LLM (openai_compat + mock) | D-112 |
| OQ-27 | Ask-on-ambiguity (clarification loop) | D-113 |
| OQ-28 | JSON Schema in system prompt + validate gate | D-114 |
