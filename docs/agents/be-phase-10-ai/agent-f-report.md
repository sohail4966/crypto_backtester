# Agent F Report — BE Phase 10: AI NL Interface (Tests)

| Field | Value |
|---|---|
| **Role** | Test coverage |
| **Status** | Complete |
| **Date** | 2026-08-11 |

---

## Coverage

| Area | File | Cases |
|---|---|---|
| Prompt / schema injection | `tests/ai/test_prompt.py` | schema keys, clarifications in user prompt |
| Providers | `tests/ai/test_providers.py` | mock default, key→openai, explicit mock |
| Translate / clarify | `tests/ai/test_translate.py` | ok, ambiguous, clarify complete, invalid DSL, empty, missing session |
| Explain | `tests/ai/test_explain.py` | nested AND template |
| HTTP | `tests/api/test_ai.py` | translate, clarify loop, 422/404, explain |

## Constraints honored

- `AI_LLM_PROVIDER=mock` forced in API tests — **no network**
- No real API keys in fixtures

## Result

`pytest tests/ai/ tests/api/test_ai.py -q` → **19 passed**
