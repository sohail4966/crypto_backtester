# Tech Design — BE Phase 9: Full Trading DSL

| Field | Value |
|---|---|
| **Status** | Ready for implementation (Agent B answers incorporated) |
| **PRD** | [prd.md](./prd.md) (Approved) |
| **Decisions** | D-109, D-110, D-111; prior D-08, D-11, D-98, D-105, D-106 |
| **HLD** | [PHASE_9_HLD.md](../../../backend/docs/PHASE_9_HLD.md) |
| **Agent D** | `dsl/` + `signals/` evaluator extensions |
| **Agent E** | **Skipped** — no REST (Q13) |
| **Answers** | [answers.md](./answers.md) |

---

## 1. Architecture Overview

```
Strategy JSON (schema_version + entry/exit trees)
        │
        ▼
┌───────────────────┐
│ dsl.validate      │  pydantic + semantic checks
│ dsl.json_schema   │  LLM-ready export
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐     optional frames{tf: OHLCV}
│ signals.evaluator │◄──── EvalContext (base_tf, frames)
│  _evaluate_condition
└─────────┬─────────┘
          │
          ├─ AND/OR/NOT / all / SEQUENCE
          ├─ indicator / field / compare / bars_ago
          ├─ timeframe → align (completed HTF)
          ├─ smc → smc.conditions
          └─ pattern → patterns.analyze_patterns
```

### Responsibilities

| Layer | Owns | Does not own |
|---|---|---|
| **`dsl/`** | Schema, validation, JSON Schema, file library | Indicator math, HTTP, screener |
| **`signals/`** | Evaluation → boolean Series | Persistence, NL translation |
| **Phase 8 screener** | (future) imports DSL validators | Grammar ownership |

---

## 2. Package layout

```
backend/
  dsl/
    __init__.py
    version.py          # SCHEMA_VERSION = "1"
    schema.py           # pydantic models
    validate.py         # validate_strategy()
    json_schema_export.py
    align.py            # HTF resample + look-ahead-safe align
    library.py          # save/load named strategies (files)
  signals/
    types.py            # extended TypedDicts
    evaluator.py        # extended evaluation
  tests/dsl/
    test_schema.py
    test_validate.py
    test_align.py
    test_sequence.py
    test_library.py
    test_evaluator_dsl.py
  data/strategies/      # default file library root (.gitkeep)
  docs/PHASE_9_HLD.md
```

### Do not modify

- Phase 8 screener packages (if present) — document import points only
- `indicators/registry.py` (import only)
- OpenAPI / FE (no Phase 9 REST)

---

## 3. Schema (canonical LLM form)

```json
{
  "schema_version": "1",
  "entry_trigger": "edge",
  "entry": {
    "op": "AND",
    "conditions": [
      {
        "indicator": "RSI",
        "params": {"period": 14},
        "timeframe": "1d",
        "op": "<",
        "value": 30
      },
      {
        "field": "close",
        "op": ">",
        "ref": {"field": "close", "bars_ago": 5}
      },
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

### Group / SEQUENCE nodes

| Node | Keys |
|---|---|
| AND / OR | `op`, `conditions` (≥1; OR/AND ≥1) |
| NOT | `op: NOT`, `conditions` length 1 |
| SEQUENCE | `op: SEQUENCE`, `conditions` (≥2), `within_bars` (≥1) |
| Legacy AND | `all: [...]` |

### Leaf nodes

| Kind | Keys |
|---|---|
| Indicator | `indicator`, `op`, `value` or `compare`, optional `params`, `timeframe`, `bars_ago` |
| Field | `field` (`open|high|low|close|volume`), `op`, `value` or `ref`/`compare` |
| SMC | `smc`, optional `side`, `params` |
| Pattern | `pattern` (PatternName string) |

---

## 4. Multi-TF alignment (D-103)

1. Resolve HTF frame: `frames[tf]` or resample base OHLCV (OHLCV agg).
2. Evaluate leaf on HTF → boolean Series indexed by HTF open.
3. Map to availability: `avail_ts = htf_open + timeframe_ms(tf)`.
4. `reindex(base_index, method="ffill")` from an availability-indexed series.
5. Bars before first completed HTF → False.

---

## 5. Evaluation API

```python
def evaluate_signals(
    candles: pd.DataFrame,
    strategy: Strategy,
    *,
    base_timeframe: str = "1d",
    frames: dict[str, pd.DataFrame] | None = None,
) -> tuple[pd.Series, pd.Series]:
    ...
```

`validate_strategy(strategy) -> StrategyModel` raises `InvalidSignalError` on failure.

---

## 6. File library

```python
save_strategy(name: str, strategy: dict, *, root: Path | None = None) -> Path
load_strategy(name: str, *, root: Path | None = None) -> dict
list_strategies(*, root: Path | None = None) -> list[str]
```

Files: `{root}/{safe_name}.json`. Validate on save and load.

---

## 7. Screener integration points (Phase 8)

| Import | Use |
|---|---|
| `dsl.validate_strategy` | Reject invalid alert/screener predicates |
| `dsl.strategy_json_schema` | Docs / admin UI |
| `signals.evaluate_signals` | Per-symbol boolean Series |
| `dsl.library.*` | Optional named presets |

Phase 9 does **not** create screener modules.

---

## 8. Test plan

| Area | File |
|---|---|
| Pydantic / JSON Schema | `test_schema.py` |
| Validation errors | `test_validate.py` |
| HTF align no lookahead | `test_align.py` |
| SEQUENCE window | `test_sequence.py` |
| File library | `test_library.py` |
| End-to-end DSL evaluate | `test_evaluator_dsl.py` |
| Legacy regression | existing `tests/signals/` |
