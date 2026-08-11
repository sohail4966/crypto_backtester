# PRD — BE Phase 9: Full Trading DSL

| Field | Value |
|---|---|
| **Status** | Approved (auto — no human-in-loop; product defaults below) |
| **Phase** | Backend Phase 9 |
| **Product intent** | [ROADMAP.md — Phase 9](../../../backend/docs/ROADMAP.md#phase-9--full-trading-dsl) |
| **Prior contracts** | D-08 (structured signals), D-11 (boolean Series), Phase 2–7 condition keys |
| **Open questions resolved** | OQ-23, OQ-24, OQ-25 → D-102–D-104 (nested tree Option A) |

---

## 1. Problem / Goal

### Problem

The signal dict today supports single-indicator legs, cross-compare, AND via `all`,
and named `smc` conditions. It cannot express OR/NOT nesting, multi-timeframe legs,
lookbacks, or sequences — the grammar LLMs and traders need before Phase 10.

### Goal

Ship a **versioned Trading DSL** that:

1. Expresses nested **AND / OR / NOT** condition trees (OQ-23 Option A).
2. Supports **cross-indicator**, **multi-timeframe** (look-ahead-safe), **bars_ago**,
   and pragmatic **SEQUENCE** conditions.
3. Provides **pydantic models + JSON Schema** for LLM-ready validation.
4. Extends evaluation without fighting Phase 8 screener (pure `dsl/` + `signals/`).
5. Optionally saves/loads **named strategies** via a simple file library.

Success: unit tests lock grammar + evaluation; Phase 10 can inject the JSON Schema
into prompts; screener can import validators later without owning the grammar.

---

## 2. User Roles

| Role | Description | Auth |
|---|---|---|
| **Library consumer (backtest / future screener / AI)** | Validates and evaluates DSL strategy dicts. | N/A |
| **Developer / QA** | Runs `pytest tests/dsl/ tests/signals/`. | Local |
| **HTTP / FE** | Not required in v1 (library-first). | — |

---

## 3. Scope

### In scope (v1)

- Package `backend/dsl/` — pydantic schema, validate, JSON Schema export, file library.
- Extend `signals/evaluator.py` + `signals/types.py` for new condition shapes.
- Backward-compatible: existing flat legs and `all:` AND groups keep working.
- `pattern:` named condition hook (uses `patterns.analyze_patterns` Series).
- `schema_version` field on strategies.
- Tests under `backend/tests/dsl/` (+ evaluator extensions in `tests/signals/`).
- `PHASE_9_HLD.md`, ROADMAP update, D-102–D-104, OQ-23–25 resolved.
- Screener integration points documented (no screener implementation).

### Out of scope / deferred

| Item | Reason |
|---|---|
| NL → DSL (LLM) | Phase 10 (OQ-26–28) |
| Screener / alerts wiring | Phase 8 (may land in parallel; import DSL later) |
| REST strategy CRUD | Optional; file library suffices for v1 |
| DB strategy table | Defer if file store is enough |
| Arbitrary expression language | Keep JSON tree only (D-08) |

---

## 4. Acceptance criteria

| ID | Criterion |
|---|---|
| **AC-1** | Nested AND/OR/NOT via `{op, conditions}` evaluates correctly |
| **AC-2** | Cross-indicator `compare` continues to work; documented in schema |
| **AC-3** | Multi-TF condition with look-ahead-safe alignment |
| **AC-4** | Lookback via `bars_ago` / `ref` |
| **AC-5** | SEQUENCE: A then B within N bars (pragmatic v1) |
| **AC-6** | `schema_version` present and validated |
| **AC-7** | Pydantic models + exported JSON Schema for LLM |
| **AC-8** | Named strategy save/load (file) works |
| **AC-9** | Validation + evaluation tests green |
| **AC-10** | PHASE_9_HLD + ROADMAP + A–H artifacts; OQ-23–25 resolved |
| **AC-11** | No Phase 8 screener file conflicts; DSL remains importable |

---

## 5. Product defaults (auto-resolved)

| Topic | Default |
|---|---|
| Grammar | **Nested tree Option A** (`op` + `conditions`) |
| Legacy `all` | Kept as AND alias |
| Multi-TF alignment | HTF signal available only after HTF bar **close** |
| SEQUENCE | Two+ ordered legs; fires on last leg when priors seen within `within_bars` |
| Strategy library | JSON files under configurable directory (default `data/strategies/`) |
| REST | Skipped in v1 |

---

## 6. Non-goals for this phase

- Choosing an LLM provider (OQ-26 stays open for Phase 10).
- Clarification UX for ambiguous NL (OQ-27).
- Prompt engineering beyond shipping the schema artifact (OQ-28).
