# Phase 9 High Level Design — Full Trading DSL

**Status:** Complete — see [Phase 9 Completion Assessment](#phase-9-completion-assessment)  
**Prerequisite:** Phase 2 indicators, Phase 6 patterns, Phase 7 SMC, Phase 8 screener slice (D-105/D-106)  
**Decisions:** D-109 (nested tree + schema_version), D-110 (lookback + SEQUENCE), D-111 (file strategy library)  
**Agent artifacts:** [docs/agents/be-phase-9-dsl/](../../docs/agents/be-phase-9-dsl/)  
**Parallel note:** Phase 8 owns `screener/`; Phase 9 owns `dsl/` + evaluator grammar extensions.
Screener continues to import `evaluate_condition` / `all|any|not`.

---

## Starting Point

Phase 8 shipped nested `all` / `any` / `not` and leaf `timeframe` (D-105, D-106).
Traders and Phase 10 still need a **versioned, LLM-ready grammar** with lookbacks,
sequences, cross-indicator docs, pattern leaves, and a JSON Schema export.

**Phase 9 goal:** Formal Trading DSL as pydantic models + evaluator extensions.

---

## Done Criteria

1. Nested AND/OR/NOT via `{op, conditions}` (Option A) **and** Phase 8 `all`/`any`/`not`.
2. Cross-indicator `compare` documented and tested.
3. Multi-TF leaf `timeframe` with as-of ffill (D-106); optional `completed_only` align.
4. Lookback via `bars_ago` / `ref`.
5. SEQUENCE (A then B within N bars) pragmatic v1.
6. `schema_version` on strategies (default `"1"`).
7. Pydantic models + `strategy_json_schema()` for LLM prompts.
8. Named strategy file library (`data/strategies/`).
9. `pytest tests/dsl/` (+ signals/screener regression) green.
10. ROADMAP Phase 9 complete; A–H artifacts present; OQ-23–25 resolved.

---

## Architecture

```
dsl/
  version.py              SCHEMA_VERSION = "1"
  schema.py               StrategyModel / ConditionModel (pydantic)
  validate.py             validate_strategy → InvalidSignalError
  json_schema_export.py   strategy_json_schema()
  align.py                resample_ohlcv + align_series_to_base
  library.py              save/load/list named JSON strategies

signals/evaluator.py      evaluate_condition / evaluate_signals
                          AND/OR/NOT/SEQUENCE + all/any/not + pattern + MTF
```

### Data flow

1. Optional `validate_strategy(dict)` before run.
2. `evaluate_signals` / `evaluate_condition` build `EvalContext`.
3. Recurse condition tree → boolean Series on base index.
4. HTF leaves: evaluate on HTF frame → as-of ffill to base (no future HTF opens).

---

## Canonical LLM form

```json
{
  "schema_version": "1",
  "entry_trigger": "edge",
  "entry": {
    "op": "AND",
    "conditions": [
      {"indicator": "RSI", "params": {"period": 14}, "timeframe": "1d", "op": "<", "value": 30},
      {"field": "close", "op": ">", "ref": {"field": "close", "bars_ago": 5}},
      {
        "op": "SEQUENCE",
        "within_bars": 10,
        "conditions": [
          {"pattern": "bullish_engulfing"},
          {"indicator": "RSI", "params": {"period": 14}, "op": ">", "value": 50}
        ]
      }
    ]
  },
  "exit": {
    "op": "OR",
    "conditions": [
      {"indicator": "RSI", "params": {"period": 14}, "op": ">", "value": 70},
      {"smc": "bos", "side": "bearish"}
    ]
  }
}
```

Phase 8 aliases remain valid inside the same tree: `all`, `any`, `not`.

---

## Screener integration points

| Import | Use |
|---|---|
| `dsl.validate_strategy` | Reject invalid scan predicates (optional hardening) |
| `dsl.strategy_json_schema` | Docs / admin / Phase 10 prompts |
| `signals.evaluate_condition` | Per `(symbol, TF)` boolean Series (already used) |
| `dsl.library.*` | Named presets for scan/backtest |

Phase 9 does **not** modify `screener/` modules.

---

## Key contracts

| Contract | Rule |
|---|---|
| Grammar | Nested Option A (`op`/`conditions`) + Phase 8 `all`/`any`/`not` |
| Boolean Series | D-11 — True where condition holds; NaN → False |
| MTF | Leaf `timeframe`; frames map required when passed; else resample |
| Align | As-of ffill on HTF open (D-106); `completed_only=True` optional |
| SEQUENCE | Last leg True at `i`; priors strictly ordered in `[i-within, i)` |
| Persistence | JSON files under `data/strategies/` (no DB migration) |
| REST | None in v1 |

---

## Phase 9 Completion Assessment

| Criterion | Status |
|---|---|
| Nested AND/OR/NOT | **Pass** |
| Cross-indicator | **Pass** |
| Multi-TF + safe align | **Pass** |
| Lookback / bars_ago | **Pass** |
| SEQUENCE | **Pass** |
| schema_version + JSON Schema | **Pass** |
| File strategy library | **Pass** |
| Tests | **Pass** (`tests/dsl` + signals + screener) |
| Docs / OQ-23–25 | **Pass** |

**Verdict:** Complete for library + evaluator scope. Phase 10 consumes
`strategy_json_schema()` for NL → DSL.
