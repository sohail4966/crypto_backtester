# Phase 2 High Level Design — Indicator Library

**Status:** Complete — see [Phase 2 Completion Assessment](#phase-2-completion-assessment)  
**Prerequisite:** Phase 1 complete ([PHASE_1_HLD.md](PHASE_1_HLD.md))  
**Next phase after this:** [Phase 3 — Backtest Engine (full)](ROADMAP.md#phase-3--backtest-engine-full)

---

## Starting Point

Phase 1 delivers stable canonical `1m` storage and derived higher-timeframe reads via
`get_candles()`. Phase 2 builds the indicator layer on top of that data foundation.

**Status:** Complete — [Phase 2 Completion Assessment](PHASE_2_HLD.md#phase-2-completion-assessment)

**Current indicator code:**

| Module | What exists | Phase 2 action |
|---|---|---|
| `indicators/talib_wrappers.py` | TA-Lib wrappers for standard indicators | **Done** |
| `indicators/custom/*.py` | SuperTrend, VWAP, Ichimoku, pivots, etc. | **Done** |
| `indicators/registry.py` | 58-key central registry + `INDICATOR_META` | **Done** |
| `signals/evaluator.py` | OHLCV routing via registry | **Done** |
| ~~`indicators/basic.py`~~ | ~~Custom pandas `sma()`, `rsi()`~~ | **Removed** (D-28) |

Phase 2 expands into a **TA-Lib-backed**, registry-based library covering the user's
**top-50 crypto indicator list** (deduplicated catalog below). TA-Lib is the reference
implementation — no per-indicator TradingView cross-checks (see D-28).

---

## Phase 2 Goal

**Any common OHLCV-based indicator can be computed from candle data in one function call
and registered for the signal evaluator.**

**Done when:**

1. All **in-scope** indicators in the catalog below are implemented, unit-tested, and
   registered.
2. Each in-scope indicator has unit tests (shape, warmup NaNs, param validation) on
   synthetic or fixture OHLCV data.
3. The signal evaluator resolves indicator names dynamically with full OHLCV input and
   separate registry keys for multi-output series.
4. Parameter validation contract is locked (D-30).
5. TA-Lib dependency is documented in `requirements.txt` with install notes for local
   dev and Docker.
6. POC custom `indicators/basic.py` is removed; RSI/SMA come from TA-Lib only (D-28).

**Explicitly out of scope for Phase 2**

- Backtest engine changes (Phase 3)
- Market structure / swing detection (Phase 4)
- Chart patterns (Phase 5)
- On-chain metrics (NVT, MVRV, Pi Cycle, Puell Multiple, etc.)
- Drawing tools that require user anchors (Fibonacci retracement/extensions, anchored VWAP)
- Volume-at-price histograms (VPVR)
- Signal DSL extensions beyond single-leg entry/exit (AND/OR — OQ-23, later phase)
- Precomputing or storing indicator values in the database (rejected in D-07)

---

## Locked Decisions

| ID | Decision | Phase 2 impact |
|---|---|---|
| D-06 | `get_candles()` is the only data boundary | Indicators receive in-memory OHLCV only |
| D-07 | Indicators are pure functions | Wrappers around TA-Lib stay side-effect free |
| D-08 | Signals are structured dicts | Registry maps dict `indicator` names to functions |
| D-27 | TA-Lib is the default engine | All standard indicators delegate to TA-Lib |
| D-28 | TA-Lib is source of truth; retire POC custom indicators | Remove `basic.py`; no TradingView validation |
| D-29 | VWAP: rolling + UTC session | `params.variant` = `rolling` (default) or `session` |
| D-30 | Invalid params raise `ValueError` | Evaluator maps to `InvalidSignalError` |
| D-31 | Separate Series arguments | `(close, *, high=, low=, volume=, **params)` |
| D-32 | Multi-output = separate registry keys | `MACD_LINE`, `MACD_SIGNAL`, `BB_UPPER`, … — no default `output` |
| D-33 | Scope: Tier 1 + Tier 2 + max feasible custom | Tier 3 items deferred (D-34) |
| D-34 | Tier 3 deferrals confirmed | VPVR, Fib, ZigZag, Puell, etc. |
| D-35 | Pivot session boundaries | Prior UTC calendar day on intraday; prior bar on `1d` |
| D-36 | Ichimoku defaults | 9, 26, 52, displacement 26 |

**Historical (POC only):** D-13 required custom Wilder RSI and TradingView spot-checks.
Superseded for Phase 2 by D-27 and D-28. POC completion remains valid.

---

## D-27 — TA-Lib as default engine

**Status:** Locked

**Decision:** Use [TA-Lib](https://ta-lib.org/) as the **default computation engine**
for standard indicators. Project code owns thin pure-function wrappers, the registry,
and parameter validation — not the underlying formulas.

```python
def ema(close: pd.Series, period: int) -> pd.Series:
    validate_period(period, min_val=1, series=close)
    return pd.Series(talib.EMA(close.values, timeperiod=period), index=close.index)
```

**Custom implementations** only when TA-Lib has no function: SuperTrend, Hull MA,
Keltner, Donchian, Ichimoku (TV-style layout), CMF, session/rolling VWAP, pivots, etc.

**Rejected:** Hand-rolling standard formulas in pandas; maintaining parallel POC custom code.

---

## D-28 — TA-Lib source of truth (no TradingView validation)

**Status:** Locked

**Decision:** Phase 2 does **not** require TradingView cross-validation. TA-Lib is the
reference implementation. Remove POC-era custom `indicators/basic.py` (`sma`, `rsi`) and
replace with TA-Lib wrappers. Tests verify structure and contracts, not chart parity.

**Supersedes:** D-13 verification requirement for Phase 2+ work. D-13 remains the
historical record for why POC used Wilder RSI during the spine validation phase.

---

## Indicator Catalog (deduplicated top 50)

The user's list contains **duplicates** (VWAP ×2, MFI ×2, Keltner ×2) and items that are
**not OHLCV series indicators**. Below is the authoritative Phase 2 catalog: **46 unique
names**, grouped by delivery tier.

### Tier 1 — Core (ship first)

High usage, mostly TA-Lib, unblocks Phase 3 stop sizing and common strategies.

| # | Indicator | Registry key(s) | Engine | Notes |
|---|---|---|---|---|
| 1 | SMA | `SMA` | TA-Lib | Replaces POC pandas implementation |
| 2 | EMA | `EMA` | TA-Lib | |
| 3 | WMA | `WMA` | TA-Lib | |
| 4 | MACD | `MACD_LINE`, `MACD_SIGNAL`, `MACD_HIST` | TA-Lib | Separate keys per D-32 |
| 13 | RSI | `RSI` | TA-Lib | Replaces POC custom Wilder implementation |
| 25 | Bollinger Bands | `BB_UPPER`, `BB_MIDDLE`, `BB_LOWER` | TA-Lib | Separate keys per D-32 |
| 26 | ATR | `ATR` | TA-Lib | Required for Phase 3 ATR stops |
| 6 | ADX | `ADX` | TA-Lib | Trend strength |
| 14 | Stochastic | `STOCH_K`, `STOCH_D` | TA-Lib | Separate keys per D-32 |
| 36 | OBV | `OBV` | TA-Lib | |
| 35 | Volume | `VOLUME` | Passthrough | Returns `candles["volume"]` |

**Tier 1 count:** 15 registry keys (multi-output indicators register each series separately).

### Tier 2 — Extended standard (TA-Lib + small wrappers)

| # | Indicator | Registry key | Engine | Notes |
|---|---|---|---|---|
| 5 | Ichimoku Cloud | `ICHIMOKU_TENKAN`, `ICHIMOKU_KIJUN`, `ICHIMOKU_SENKOU_A`, `ICHIMOKU_SENKOU_B`, `ICHIMOKU_CHIKOU` | Custom | D-36 defaults (9, 26, 52, disp 26) |
| 7 | Parabolic SAR | `SAR` | TA-Lib | |
| 15 | Stochastic RSI | `STOCHRSI_K`, `STOCHRSI_D` | TA-Lib | Separate keys per D-32 |
| 16 | CCI | `CCI` | TA-Lib | Needs high/low/close |
| 17 | Williams %R | `WILLR` | TA-Lib | |
| 18 | MFI | `MFI` | TA-Lib | Needs HLCV |
| 19 | ROC | `ROC` | TA-Lib | |
| 27 | Standard Deviation | `STDDEV` | TA-Lib | |
| 40 | Accumulation/Distribution | `AD` | TA-Lib | |
| 41 | Chaikin Money Flow | `CMF` | Custom | TA-Lib `ADOSC` ≠ CMF |
| 33 | Bollinger Band Width / %B | `BBP` | Derived | From BB TA-Lib outputs |
| 28 | Donchian Channels | `DONCHIAN_UPPER`, `DONCHIAN_LOWER`, `DONCHIAN_MIDDLE` | Custom | Rolling high/low |
| 47 | Pivot Points | `PIVOT_P`, `PIVOT_R1`, `PIVOT_S1`, … | Custom | D-35 session rules |

### Tier 2 — Custom (no reliable single TA-Lib call)

| # | Indicator | Registry key | Engine | Notes |
|---|---|---|---|---|
| 8 | SuperTrend | `SUPERTREND` | Custom | ATR + direction flip; very common in crypto |
| 9 | VWAP | `VWAP` | Custom | D-29: `variant=rolling` (default) or `session` |
| 10 | Hull Moving Average | `HMA` | Custom | WMA-based; not in TA-Lib |
| 11 | Keltner Channels | `KELTNER_UPPER`, `KELTNER_MIDDLE`, `KELTNER_LOWER` | Custom | EMA mid + ATR bands |
| 29 | Chandelier Exit | `CHANDELIER` | Custom | ATR trailing stop |
| 32 | Historical Volatility | `HISTVOL` | Custom | Log-return stdev, annualized |
| 34 | Volatility Rank | `VOLRANK` | Custom | Percentile rank of ATR or HV |
| 42 | Volume Oscillator | `VOLOSC` | Custom | Short/long volume MA diff |
| 43 | NVI | `NVI` | Custom | Negative Volume Index |
| 44 | PVI | `PVI` | Custom | Positive Volume Index |
| 20 | TSI | `TSI` | Custom | Double-smoothed momentum |
| 21 | Awesome Oscillator | `AO` | Custom | Median price SMA difference |
| 22 | Qstick | `QSTICK` | Custom | EMA of (close − open) |
| 30 | Volatility Oscillator | `VOLOSCILLATOR` | Custom | Define TV-aligned formula in implementation |

### Tier 3 — Variants / lower priority (Phase 2 stretch or defer)

| # | Indicator | Status | Reason |
|---|---|---|---|
| 12 | Guppy MACD | **Defer** | MACD variant (multiple EMA groups); niche vs standard MACD |
| 23 | Elder-RSI | **Defer** | RSI + EMA filter; compose from Tier 1/2 in signals later |
| 24 | KDJ | **Defer** | Regional Stochastic variant; add if TV validation demand exists |
| 37 | VPVR | **Defer → Phase 4+** | Volume profile by price level — not a time-series indicator |
| 45 | Fibonacci Retracement | **Defer → Phase 4+** | Requires swing anchors / user-drawn range |
| 46 | Fibonacci Extensions | **Defer → Phase 4+** | Same |
| 48 | Copenhagen Index | **Defer** | Obscure; no clear TV default |
| 49 | ZigZag | **Defer → Phase 4** | Structure detection; lookahead concerns (OQ-10 territory) |
| 50 | Puell Multiple | **Defer → on-chain phase** | Miner revenue / BTC supply — not OHLCV |

### On-chain metrics (informational — not Phase 2)

NVT, Daily Active Addresses, Miners' Revenue, Pi Cycle Top, MVRV Z-Score — require
external data feeds, not candle OHLCV. Track as a future **Phase 2b or Phase 7**
workstream if needed.

### Summary counts

| Category | Count |
|---|---|
| Unique names in user list | 50 |
| After deduplication | 46 |
| Tier 1 (must ship) | 15 registry keys |
| Tier 2 (in-scope Phase 2) | ~40+ registry keys |
| Tier 3 deferred | 9 |
| On-chain (out of scope) | 5+ |

**Phase 2 target (D-33):** Tier 1 + all Tier 2 TA-Lib indicators + as many Tier 2 custom
implementations as feasible in one phase. Tier 3 remains deferred (D-34).

---

## Architecture

### Layering

```
get_candles() → pd.DataFrame (OHLCV)
       │
       ▼
indicators/registry.py  ──►  pure fn(close | ohlcv, **params) → pd.Series
       │                      │
       │                      ├── talib_wrappers.py  (TA-Lib engine — all standard indicators)
       │                      └── custom/*.py        (SuperTrend, VWAP, Ichimoku, …)
       │
       ▼
signals/evaluator.py  ──►  INDICATORS[name](candles, **params) → Series
       │
       ▼
evaluate_signals() → entry/exit boolean Series
```

D-07 is preserved: wrappers may call TA-Lib internally but expose the same pure-function
contract as today.

### Module layout (target)

```
indicators/
  __init__.py           # public re-exports for tests and scripts
  registry.py           # INDICATORS dict + INDICATOR_META (inputs per key)
  talib_wrappers.py     # SMA, EMA, RSI, MACD_*, BB_*, ATR, ADX, STOCH_*, …
  custom/
    __init__.py
    supertrend.py
    vwap.py
    ichimoku.py
    hull.py
    keltner.py
    donchian.py
    pivots.py
    volume_indexes.py   # NVI, PVI, vol oscillator
    …
  validation.py         # shared param validators

tests/
  fixtures/
    btc_usdt_1d_ohlcv.csv   # full OHLCV for integration-style unit tests
  indicators/
    test_talib_wrappers.py
    test_custom_*.py
    test_registry.py
  signals/
    test_evaluator.py       # MACD_HIST, MFI, unknown indicator
```

POC `indicators/basic.py` and TV regression tests are **removed** during Step 1 (D-28).

### Registry design

Central registry replaces the inline dict in `signals/evaluator.py`. **Each output
series is its own registry key** (D-32) — no `output` param in signal dicts.

```python
# indicators/registry.py (conceptual)

INDICATORS: dict[str, IndicatorFn] = {
    "RSI": rsi,
    "SMA": sma,
    "EMA": ema,
    "MACD_LINE": macd_line,
    "MACD_SIGNAL": macd_signal,
    "MACD_HIST": macd_histogram,
    "BB_UPPER": bb_upper,
    "BB_MIDDLE": bb_middle,
    "BB_LOWER": bb_lower,
    "STOCH_K": stoch_k,
    "STOCH_D": stoch_d,
    "ATR": atr,
    # …
}

INDICATOR_META: dict[str, IndicatorMeta] = {
    "RSI": {"inputs": ["close"]},
    "MACD_LINE": {"inputs": ["close"], "shared_params": ("fast", "slow", "signal")},
    "MFI": {"inputs": ["high", "low", "close", "volume"]},
}
```

Example signal (explicit series — no ambiguity):

```python
{
    "entry": {
        "indicator": "MACD_HIST",
        "params": {"fast": 12, "slow": 26, "signal": 9},
        "op": ">",
        "value": 0,
    },
}
```

Multi-output TA-Lib calls (e.g. `talib.MACD`) are computed once per param set inside
shared internal helpers; each registry wrapper returns one Series. Cache within a single
`evaluate_signals()` call is optional optimization — not required for Phase 2 MVP.

`signals/evaluator.py` imports `INDICATORS` from `indicators.registry`.

### Input routing (OHLCV)

Today `_resolve_indicator` only passes `close`. Phase 2 uses **separate Series
arguments** (D-31):

```python
def _call_indicator(fn: IndicatorFn, candles: pd.DataFrame, meta: IndicatorMeta, params: dict) -> pd.Series:
    kwargs = {col: candles[col] for col in meta["inputs"] if col != "close"}
    if "close" in meta["inputs"]:
        return fn(candles["close"], **kwargs, **params)
    return fn(**kwargs, **params)
```

### Parameter validation (D-30)

**Locked contract:**

| Case | Behavior |
|---|---|
| `period < 1` (or invalid type) | Raise `ValueError` with clear message |
| `len(series) < period` | Raise `ValueError` |
| Unknown registry key | `InvalidSignalError` in evaluator |
| Warmup bars (valid params, insufficient history) | Return `NaN` — no exception |
| Evaluator boundary | Catch `ValueError` from indicators → `InvalidSignalError` |

**Industry practice:** Libraries like TA-Lib, pandas, and NumPy use **fail-fast**
exceptions for invalid arguments (`ValueError`, `TypeError`). Silent NaN on bad params
is rare and makes AI/YAML mistakes hard to debug. Warmup NaNs for insufficient *warmup
length* (valid period, series too short for first computed value) are normal and stay
as NaN — that is not an error condition.

Shared helpers in `indicators/validation.py`:

```python
def validate_period(period: int, *, min_val: int, series: pd.Series) -> None: ...
```

---

## Testing Strategy (D-28)

No TradingView cross-validation. Tests verify **contracts and correctness properties**:

| Layer | Requirement |
|---|---|
| Unit | Param validation raises `ValueError`; warmup NaN count matches period |
| Shape | Output index aligns with input; dtype float |
| Synthetic | Hand-calculable cases on short Series (e.g. SMA(3) on [10,20,30]) |
| Fixture | Optional BTC/USDT 1d OHLCV fixture for smoke tests (not TV baselines) |
| Registry | Every key has meta + callable; no duplicate keys |
| Evaluator | Unknown indicator, MACD_HIST/MFI legs, error mapping |
| Non-regression | Default RSI strategy in `config.yaml` still runs after TA-Lib migration |

**Coverage target:** Every Tier 1 and Tier 2 registry key has structural unit tests.
Custom indicators document the chosen formula in the function docstring.

---

## Signal Evaluator Changes

| Change | Detail |
|---|---|
| Import registry | `from indicators.registry import INDICATORS, INDICATOR_META` |
| OHLCV routing | Pass high/low/volume per `INDICATOR_META` (D-31) |
| Multi-output | Separate registry keys — no `output` param (D-32) |
| Error mapping | `ValueError` → `InvalidSignalError` (D-30) |
| POC cleanup | Remove import of `indicators.basic` |

No change to `OPS`, look-ahead semantics, or `evaluate_signals` return shape.

---

## Dependencies

### Python packages

Add to `requirements.txt`:

```
TA-Lib>=0.6.0
```

Existing stack unchanged: `pandas`, `ccxt`, `psycopg`, etc.

### Local install

macOS (verified in dev): `pip install TA-Lib` pulls a wheel with bundled native lib.

Linux / Docker: prefer PyPI wheel if available for target platform; otherwise install
system `ta-lib` C library before pip. Document in project README when implementing —
not blocking HLD approval.

### Version pin

Pin exact version after first green CI run (e.g. `TA-Lib==0.6.8`) to avoid silent
native library drift.

---

## Build Order

Each step is independently verifiable. Do not start step N+1 until step N passes.

### Step 0 — Q&A gate

**Complete.** Decisions D-27 through D-36 recorded in [DECISIONS.md](DECISIONS.md).
OQ-08 through OQ-38 resolved in [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).

---

### Step 1 — Infrastructure

**Build**

- Add `TA-Lib` to `requirements.txt`.
- Create `indicators/registry.py`, `indicators/validation.py`, `indicators/talib_wrappers.py`.
- Move `INDICATORS` out of `signals/evaluator.py`.
- Remove `indicators/basic.py`; migrate tests to `test_talib_wrappers.py`.

**Verify**

```bash
pip install -r requirements.txt
pytest tests/indicators/test_registry.py -q
python -c "import talib; from indicators.registry import INDICATORS; print(len(INDICATORS))"
```

---

### Step 2 — Tier 1 indicators

**Build**

- Implement Tier 1 registry keys (TA-Lib wrappers + separate MACD/BB/STOCH keys).
- Structural unit tests for each (no TV baselines).

**Verify**

```bash
pytest tests/indicators/ -q
pytest tests/signals/test_evaluator.py -q
```

---

### Step 3 — Evaluator OHLCV + registry keys

**Build**

- `_resolve_indicator` uses `INDICATOR_META` input routing (D-31).
- Tests: `MACD_HIST` condition, MFI with full OHLCV.

**Verify**

```bash
pytest tests/signals/ -q
# Manual: run_poc.py / run_backtest.py still pass with RSI strategy
```

---

### Step 4 — Tier 2 TA-Lib batch

**Build**

- SAR, STOCHRSI, CCI, WILLR, MFI, ROC, STDDEV, AD.
- CMF custom to TV spec.
- BBP derived from BBANDS.

**Verify**

- Per-indicator structural tests + registry completeness check.

---

### Step 5 — Tier 2 custom batch

**Build**

- SuperTrend, VWAP (D-29 both variants), HMA, Keltner, Donchian, Ichimoku (D-36),
  Chandelier, HistVol, VolRank, volume indexes, AO, Qstick, TSI, Volatility Oscillator,
  Pivots (D-35).

**Verify**

- Structural tests for each; prioritize SuperTrend, VWAP, Ichimoku.

---

### Step 6 — Documentation and phase sign-off

**Build**

- Update `ROADMAP.md` Phase 2 section with link to this HLD.
- Record D-27+ in `DECISIONS.md`.
- Close OQ-08, OQ-09 in `OPEN_QUESTIONS.md`.
- Phase 2 completion assessment section in this doc (mirror Phase 1).

**Verify**

- Full test suite green.
- Checklist in [Done Criteria](#done-criteria) satisfied.

---

## Done Criteria

Phase 2 is complete when all of the following are true:

| # | Criterion |
|---|---|
| 1 | D-27 through D-36 recorded in DECISIONS.md |
| 2 | Tier 1 registry keys implemented and tested |
| 3 | Tier 2 in-scope indicators implemented (TA-Lib + custom per D-33) |
| 4 | Tier 3 items remain deferred (D-34) |
| 5 | `signals/evaluator.py` uses central registry with OHLCV routing (D-31, D-32) |
| 6 | POC `indicators/basic.py` removed (D-28) |
| 7 | `pytest` full suite passes |
| 8 | `run_poc.py` / `run_backtest.py` work with TA-Lib RSI strategy |
| 9 | No indicator module imports `data.*` or opens DB connections |

---

## Phase 2 Completion Assessment

**Assessment date:** 2026-06-06  
**Rating:** **9 / 10**  
**Completion:** **100% for Phase 2 scope**

Phase 2 is complete for the accepted scope (Tier 1 + Tier 2 TA-Lib + Tier 2 custom per
D-33). The indicator layer is TA-Lib-backed with a central registry of **58 keys**,
OHLCV-aware signal evaluation, structural unit tests, and POC custom indicators removed.
Tier 3 items remain deferred per D-34.

### Evidence checked

| Check | Result | Notes |
|---|---|---|
| Full unit suite | Passing | `278 passed` |
| D-27 through D-36 recorded | Done | [DECISIONS.md](DECISIONS.md) |
| Tier 1 registry keys | Done | 16 keys (SMA, EMA, WMA, MACD×3, RSI, BB×3, ATR, ADX, STOCH×2, OBV, VOLUME) |
| Tier 2 TA-Lib batch | Done | SAR, STOCHRSI×2, CCI, WILLR, MFI, ROC, STDDEV, AD, CMF, BBP |
| Tier 2 custom batch | Done | SuperTrend, VWAP, HMA, Keltner×3, Donchian×3, Ichimoku×5, Pivots×7, Chandelier, HistVol, VolRank, VOLOSC, NVI, PVI, TSI, AO, QSTICK, VOLOSCILLATOR |
| Tier 3 deferrals | Confirmed | Guppy MACD, Elder-RSI, KDJ, VPVR, Fib, ZigZag, Puell, Copenhagen — not implemented |
| Central registry | Done | `indicators/registry.py` — 58 keys, matching `INDICATOR_META` |
| Evaluator OHLCV routing | Done | `_call_indicator()` per D-31; `ValueError` → `InvalidSignalError` per D-30 |
| POC `basic.py` removed | Done | Replaced by `indicators/talib_wrappers.py` |
| TA-Lib dependency | Done | `TA-Lib==0.6.8` in `requirements.txt`; install notes in README |
| Pure functions (D-07) | Verified | No `data.*` imports under `indicators/` |
| Non-regression | Passing | `run_poc.py` / RSI strategy path via `tests/test_run_poc*.py` |

### Rating breakdown

| Area | Score | Comment |
|---|---|---|
| Architecture alignment | 9/10 | Registry, TA-Lib wrappers, custom modules match HLD layout |
| Tier 1 coverage | 10/10 | All keys implemented and structurally tested |
| Tier 2 coverage | 9/10 | Full TA-Lib batch + all planned custom indicators shipped |
| Evaluator integration | 9/10 | OHLCV routing, multi-output keys, error mapping in place |
| Test coverage | 9/10 | Per-key registry smoke tests; focused custom indicator tests |
| Documentation | 8/10 | HLD, ROADMAP, DECISIONS updated; README layout refreshed |

### Completion verdict

Phase 2 is **complete**. Phase 3 (full backtest engine) can start from this indicator foundation.

---

## Resolved Q&A (2026-06-06)

| ID | Question | Decision |
|---|---|---|
| D-27 / OQ — | TA-Lib as default engine? | **Yes** |
| D-28 | TradingView validation / POC custom RSI? | **No TV validation; remove POC custom indicators; TA-Lib only** |
| OQ-08 / D-29 | VWAP variant? | **Both** — rolling (default) + UTC session via `params.variant` |
| OQ-09 / D-30 | Param validation? | **`ValueError`** (fail-fast; industry standard) |
| OQ-32 / D-31 | Function signature? | **Separate Series arguments** |
| OQ-33 / D-32 | Multi-output? | **Separate registry keys** (`MACD_HIST`, not `MACD` + default line) |
| OQ-34 / D-33 | Scope? | **Tier 1 + Tier 2 TA-Lib + as many custom as feasible** |
| OQ-35 / D-34 | Tier 3 deferrals? | **Confirmed defer** |
| OQ-36 / D-35 | Pivot session? | **UTC calendar day on intraday; prior bar on `1d`** |
| OQ-37 | SMA? | **TA-Lib only** |
| OQ-38 / D-36 | Ichimoku defaults? | **Yes** — 9, 26, 52, displacement 26 |

---

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| TA-Lib install fails on CI/Docker | Pin wheel; document apt/brew fallback |
| Custom indicator formula ambiguity | Document formula in docstring; synthetic tests |
| Derived TF VWAP performance on long `1m` history | Accept for Phase 2; derived-TF perf (OQ-31) later |
| Scope creep (50 literal implementations) | Tier 3 deferrals (D-34); D-33 caps in-scope work |
| Large registry (multi-output keys) | Shared internal helpers; one TA-Lib call per param set |
| TA-Lib vs chart platform drift | Accepted trade-off per D-28; TA-Lib is reference |

---

## Relationship to Later Phases

| Phase 2 output | Consumer |
|---|---|
| ATR, SuperTrend, Chandelier | Phase 3 stop loss and position sizing |
| ADX, MACD, RSI | Phase 3+ strategy examples |
| Pivot / Donchian | Phase 4 structure (swing context) |
| Deferred Fib / ZigZag | Phase 4–5 |
| Registry + validation habit | Phase 7 screener (batch indicator compute) |

Phase 2 must not change backtest execution semantics (D-14) or the `get_candles()` API (D-06).

---

## References

- [PHASE_1_HLD.md](PHASE_1_HLD.md) — data foundation (complete)
- [ROADMAP.md](ROADMAP.md) — platform phase map
- [DECISIONS.md](DECISIONS.md) — D-07, D-08, D-27 through D-36
- [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) — OQ-08 through OQ-38 resolved
- [CONVENTIONS.md](CONVENTIONS.md) — pure functions, registry pattern, TV golden tests
- [POC_HLD.md](POC_HLD.md) — original indicator step 3 validation habit
