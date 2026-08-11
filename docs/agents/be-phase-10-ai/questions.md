# Clarifying Questions — BE Phase 10: AI Natural Language Interface

Review of [prd.md](./prd.md), ROADMAP Phase 10, OQ-26–28, and Phase 9 `dsl/`.
Questions only — no proposed answers.

---

## Provider / LLM

### Q1 — Provider interface

**Question:** Should providers implement a single `complete(system, user) -> str`
(raw JSON text) with the translate service owning parse/validate, or return a
structured `ProviderResult` already parsed?

### Q2 — Default when no API key

**Question:** Confirm default provider is `mock` when `AI_LLM_API_KEY` is unset,
and `openai_compat` when set (unless `AI_LLM_PROVIDER` overrides)?

### Q3 — OpenAI-compatible surface

**Question:** Confirm HTTP uses `POST {base}/chat/completions` with
`response_format: {type: "json_object"}` when supported, model from `AI_LLM_MODEL`?

---

## Ambiguity / sessions

### Q4 — Ambiguity detection owner

**Question:** Does the **LLM** decide `needs_clarification` (prompted), or does a
deterministic rules layer pre-screen vague phrases?

### Q5 — Session storage

**Question:** Confirm in-memory clarification sessions (TTL optional) for v1 — no DB?

### Q6 — Clarify contract

**Question:** Confirm `POST /ai/clarify` takes `session_id` + `answers: {question_id: text}`
and re-invokes translation with prior context?

---

## Validation / prompt

### Q7 — Schema injection

**Question:** Confirm system prompt includes `strategy_json_schema()` JSON and
instructs the model to emit only the response envelope (`status` + `strategy` or
`questions`)?

### Q8 — Invalid LLM strategy

**Question:** On schema validation failure, return HTTP 422 with machine code, or
retry once, or convert to clarification?

### Q9 — Few-shot examples

**Question:** Include 1–2 hardcoded NL→DSL examples in the prompt for v1?

---

## API / explain / scope

### Q10 — Route prefix

**Question:** Confirm `/api/v1/ai/translate|clarify|explain` with no auth?

### Q11 — Explain implementation

**Question:** Confirm template/stub explain (no LLM required) for v1?

### Q12 — Backtest narrative / suggestions

**Question:** Confirm deferred to a later slice (out of Phase 10 v1 Done When)?

### Q13 — Combined vs split endpoints

**Question:** Prefer separate translate + clarify (as listed) rather than a single
combined chat endpoint?

### Q14 — Phase 11 auth files

**Question:** Confirm AI work must not modify auth/JWT scaffolding if Phase 11 lands
in parallel — only touch `/ai` package + router registration?
