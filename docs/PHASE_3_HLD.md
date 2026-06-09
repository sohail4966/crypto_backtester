# Phase 3 High Level Design — Backtest Engine (full)

**Status:** Complete — see [Phase 3 Completion Assessment](#phase-3-completion-assessment)  
**Prerequisite:** Phase 2 complete ([PHASE_2_HLD.md](PHASE_2_HLD.md))  
**Next phase after this:** [Phase 4 — Client API Layer](ROADMAP.md#phase-4--client-api-layer-rest--websocket)

---

## Starting Point

Phase 2 delivers a 58-key indicator registry and OHLCV-aware signal evaluation. Phase 3
turns the POC backtest skeleton into a **trustworthy simulation engine** — fees, sizing,
stops, full metrics, benchmark comparison, and reproducible trade logs.

**Important:** Some Phase 3–adjacent work has already landed in the repo (ahead of this
HLD). The table below separates **done pre-work** from **remaining Phase 3 scope**.

### Current backtest / signal code

| Module | What exists today | Phase 3 status |
|---|---|---|
| `backtest/engine.py` | Bar loop; D-14; long + short; sizing; intrabar risk; cash + equity | **Done** |
| `backtest/fills.py` | `FillModel`, `CostModel` (slippage + commission) | **Done** |
| `backtest/risk.py` | Fixed/ATR/trailing stops; fixed + RR take profit | **Done** |
| `backtest/sizing.py` | Four sizing modes + per-side override | **Done** |
| `backtest/metrics.py` | Extended metrics + equity PNG | **Done** |
| `backtest/benchmark.py` | Buy-and-hold return | **Done** |
| `backtest/export.py` | Trades CSV (D-44) | **Done** |
| `backtest/types.py` | `BacktestConfig`, extended `BacktestMetrics`, `Trade` | **Done** |
| `signals/evaluator.py` | AND/`compare`/dual eval; `entry_trigger` edge/level (D-52) | **Done** |
| `signals/types.py` | Stop/TP/sizing types; `EntryTrigger` | **Done** |
| `config.py` | `backtest` block parsing; D-51 validation | **Done** |
| `run_backtest.py` | Full pipeline: metrics, benchmark, CSV export | **Done** |

### POC assumptions superseded (D-10)

D-10 locked the POC engine as long-only, one position, 100% capital, no fees. Phase 3
**extends** D-10 rather than replacing D-14. Historical POC completion remains valid.

---

## Phase 3 Goal

**Backtest results are trustworthy enough to make strategy decisions from.**

A run of `python run_backtest.py` must produce:

1. Realistic fills (D-14 + configurable slippage)
2. Configurable position sizing and costs (commission)
3. Complete risk exits (fixed, ATR, trailing stop; fixed and RR take profit)
4. Long and short support (already partial)
5. Extended performance analytics (Sharpe, Sortino, Calmar, profit factor)
6. Benchmark comparison vs buy-and-hold on the traded symbol
7. CSV export of the full trade log
8. Stable, deterministic output on repeated runs with the same data and config

**Done when:** All items in [Done Criteria](#done-criteria) pass and the full test suite is green.

**Explicitly out of scope for Phase 3**

- Market structure / swing detection (Phase 4)
- Pattern recognition (Phase 5)
- SMC (Phase 6)
- Multi-symbol portfolio backtests (Phase 7 screener territory)
- Walk-forward optimization / parameter sweeps (research tooling later)
- Web UI / chart overlays
- Live trading / order routing
- OR / NOT signal groups (OQ-23 — defer; AND is already supported)
- Margin, leverage, funding rates, liquidations
- Partial fills, order book simulation, tick-level fills

---

## Locked Decisions

| ID | Decision | Phase 3 impact |
|---|---|---|
| D-06 | `get_candles()` is the only data boundary | Engine receives in-memory OHLCV only |
| D-07 | Indicators are pure functions | ATR for stops computed before `run_backtest()` |
| D-08 | Signals are structured dicts | Risk config lives in YAML strategy blocks |
| D-14 | Entry/exit at **next-bar open** (hardcoded) | Signal exits stay on N+1 open; intrabar stops use high/low |
| D-24 | Backtest does not fetch data | `run_sync.py` must run first |
| D-28 | TA-Lib indicators | ATR stop uses registry `ATR` |
| D-37 | Intrabar stop/TP before signal exit | Stop checked first on breach bar |
| D-38 | Slippage **5 bps** production default | Tests use 0 bps |
| D-39 | Commission **0.1%** per fill default | Tests use 0 |
| D-40 | Four sizing modes | full_capital, fixed_pct, fixed_notional, risk_pct |
| D-41 | Trailing atr + fixed_pct; starts after entry bar | Not on entry bar |
| D-42 | Benchmark per strategy: `symbol` \| `none` | Not always BTC |
| D-43 | One position only | Multi-position → Phase 7 |
| D-44 | Trades CSV every run | `output/trades.csv` |
| D-45 | Sharpe, Sortino, Calmar, profit factor | Extended metrics |
| D-46 | Daily equity resample for intraday Sharpe | See OQ-39 below |
| D-47 | Every exit closes 100% of position | Complete liquidation; no partial exits |
| D-51 | risk_pct requires stop_loss | ValueError at startup if missing |
| D-48 | Full Phase 3 one pass | No MVP sub-phase |
| D-49 | Dual strategy: one net position | Long or short, not both |
| D-52 | Entry trigger edge vs level | Default `edge`; fixes intraday re-entry churn |

---

## Feature Catalog (ROADMAP → implementation plan)

| # | Feature | Current state | Phase 3 target |
|---|---|---|---|
| 1 | Long positions | Done | Keep |
| 2 | Short positions | Done (dual strategy) | Done |
| 3 | Stop loss — fixed price | Done | `fixed` with `offset_pct` or `price` |
| 4 | Stop loss — ATR | Done | Intrabar high/low (D-37) |
| 5 | Stop loss — trailing | Done | `atr_trail`, `fixed_pct_trail` (D-41) |
| 6 | Take profit — fixed price | Done | `take_profit: {type: fixed, offset_pct: …}` |
| 7 | Take profit — risk-reward | Done | `risk_reward` ratio |
| 8 | Position sizing — fixed notional | Done | `fixed_notional` |
| 9 | Position sizing — fixed % equity | Done | `fixed_pct` |
| 10 | Position sizing — risk-based (ATR) | Done | `risk_pct` + stop (D-51) |
| 11 | Commissions | Done | `percent` or `flat` (D-39) |
| 12 | Slippage | Done | Fixed bps (D-38) |
| 13 | Multiple concurrent positions | Deferred | **Phase 7** (D-43: one position only) |
| 14 | Sharpe / Sortino / Calmar / profit factor | Done | Daily resample intraday (D-46) |
| 15 | Benchmark (buy-and-hold) | Done | Per-strategy `symbol` or `none` (D-42) |
| 16 | Trade CSV export | Done | `output/trades.csv` (D-44) |
| 17 | Deterministic reruns | Done | No randomness; pure functions |
| 18 | Entry edge trigger | Done (post-HLD) | `entry_trigger: edge \| level` (D-52) |

---

## Decision detail (D-37 — D-49)

### D-37 — Execution model: signal vs intrabar risk

**Status:** Locked

**Decision:**

| Event type | Fill price | Timing |
|---|---|---|
| Signal entry / exit | `open[N+1]` ± slippage | D-14 invariant |
| Stop loss / take profit (intrabar) | Stop/target price ± slippage | Same bar as breach (use high/low) |
| Forced close (last bar) | `close[N]` ± slippage | End of data; flagged in metrics |

**Intrabar priority when both stop and target hit same bar:** stop loss first (current
behavior — conservative for longs).

**Rejected:** Signal exits at signal-bar close (look-ahead).

---

### D-38 — Slippage model

**Status:** Locked

**Decision:** Simple fixed slippage in **basis points** applied adversely to each fill:

- Long entry: `fill = price * (1 + slippage_bps/10000)`
- Long exit: `fill = price * (1 - slippage_bps/10000)`
- Short entry/exit: inverse

Production default: **`5` bps** (minimal for liquid USDT spot). Tests: **`0` bps**.

**Rejected for Phase 3:** Volume-based or spread models.

---

### D-39 — Commission model

**Status:** Locked

**Decision:** Configurable per side:

- `type: percent` — `rate` applied to notional (entry and exit)
- `type: flat` — fixed USD (or quote currency) per fill

Production default: **`rate: 0.001`** (0.1%). Tests: **`0`**.

Commissions reduce cash at fill time; equity reflects net PnL.

---

### D-40 — Position sizing

**Status:** Locked

**Decision:** One sizing mode per strategy (or per side in dual strategies):

| Mode | Config | Behavior |
|---|---|---|
| `full_capital` | (default) | Current behavior — 100% equity per trade |
| `fixed_pct` | `pct: 0.10` | Allocate fraction of current equity |
| `fixed_notional` | `amount: 1000` | Fixed quote-currency size; skip if insufficient cash |
| `risk_pct` | `risk_pct: 0.01`, requires ATR stop | Size so stop distance risks X% of equity |

Uninvested cash stays in equity curve (important for partial sizing + benchmark).

**Rejected for Phase 3:** Kelly criterion, pyramiding, scale-in/out.

---

### D-41 — Trailing stop

**Status:** Locked

**Decision:** Trailing stop types:

| Type | Config | Behavior |
|---|---|---|
| `atr_trail` | `period`, `multiplier` | Trail = best price since entry ∓ ATR×mult (long: max high) |
| `fixed_pct_trail` | `trail_pct: 0.05` | Trail = best price × (1 ∓ pct) |

Ratchet only in the favorable direction. First check on the **bar after entry** (not
entry bar). Emits `exit_reason: "trailing_stop"`.

**Note:** `CHANDELIER` indicator exists in Phase 2 but Phase 3 trailing is **engine logic**,
not an indicator call — keeps simulation in one place.

---

### D-42 — Benchmark default

**Status:** Locked — resolves OQ-17

**Decision:** Per-strategy `benchmark: symbol | none`:

- `symbol` — buy-and-hold the backtested pair (same window, `close` prices)
- `none` — skip benchmark metrics for that strategy

Example: trend-following strategies use `symbol`; strategies where B&H is meaningless
may use `none`.

---

### D-43 — Multiple positions

**Status:** Locked — resolves OQ-16

**Decision:** Phase 3 is **one position only** (`max_positions: 1`). Multiple concurrent
positions deferred to **Phase 7**. Dual strategies remain one net position (D-49).

---

### D-44 — Trade log export

**Status:** Locked

**Decision:** Every run writes `output/trades.csv` (path configurable) with columns:

`entry_date`, `exit_date`, `side`, `entry_price`, `exit_price`, `return_pct`, `exit_reason`,
`forced_close`, `size`, `commission_paid`, `pnl_quote`

---

### D-45 — Extended metrics

**Status:** Locked

**Decision:** Add to `BacktestMetrics`:

| Metric | Notes |
|---|---|
| `sharpe_ratio` | Daily equity returns when timeframe < 1d (D-46); else per-bar |
| `sortino_ratio` | Downside deviation only |
| `calmar_ratio` | CAGR / abs(max drawdown) |
| `profit_factor` | Gross wins / gross losses (quote PnL) |
| `benchmark_return` | Buy-and-hold total return |
| `alpha_vs_benchmark` | Strategy return − benchmark return (simple, not CAPM) |

Use **daily-equity resampling** when timeframe < 1d for Sharpe/Sortino (D-46).

---

## Architecture

### Layering (unchanged boundary)

```
get_candles() → pd.DataFrame
       │
       ▼
signals/evaluator.py → entry/exit boolean Series (+ dual side)
       │
       ▼
indicators/registry (ATR etc.) → auxiliary Series for risk
       │
       ▼
backtest/engine.py → trades[], equity Series
       │
       ▼
backtest/metrics.py → BacktestMetrics + benchmark
       │
       ▼
run_backtest.py → logs, equity PNG, trades CSV
```

No database access inside `backtest/` or `signals/`.

### Module layout (target)

```
backtest/
  engine.py          # bar loop, fills, stops, sizing, costs
  metrics.py         # extended stats + benchmark
  types.py           # Trade, BacktestMetrics, BacktestConfig types
  export.py          # NEW — write trades CSV
  benchmark.py       # NEW — buy-and-hold equity + return

config.yaml          # backtest: slippage, commission, sizing defaults
signals/types.py     # extend StopLossConfig, TakeProfitConfig, SizingConfig

tests/backtest/
  test_engine.py     # fills, stops, trailing, sizing, fees
  test_metrics.py    # sharpe, profit factor, benchmark
  test_export.py     # CSV shape

tests/
  test_run_backtest_integration.py  # main() path with mocked DB
```

### Engine refactor (minimal)

Keep the bar loop in `run_backtest()` but extract:

- `FillModel` — applies slippage to a raw price
- `CostModel` — commission on notional
- `Position` dataclass — side, size, entry, stop state, trail high/low
- `RiskManager` — update trailing, check intrabar stop/TP

Pure functions where possible; loop orchestrates state transitions.

### Config shape (proposed)

Top-level `backtest` block in `config.yaml` (global defaults; per-strategy override optional later):

```yaml
backtest:
  slippage_bps: 5        # D-38 — minimal for liquid USDT spot (BTC/ETH/SOL)
  commission:
    type: percent
    rate: 0.001          # D-39 — 0.1% per fill
  sizing:
    mode: full_capital   # full_capital | fixed_pct | fixed_notional | risk_pct
    pct: 1.0
  export_trades: true
  trades_csv: output/trades.csv

strategies:
  rsi_mean_reversion:
    benchmark: none      # D-42 — optional per strategy
    entry: { ... }
    exit: { ... }

  supertrend_ema_dual:
    benchmark: symbol    # buy-and-hold same pair
    long:
      entry: { ... }
      exit: { ... }
      stop_loss:
        type: atr_trail    # atr | fixed | atr_trail | fixed_pct_trail
        period: 14
        multiplier: 2.0
      take_profit:
        type: risk_reward
        ratio: 2.0
      sizing:
        mode: risk_pct
        risk_pct: 0.01
```

Existing strategies without a `backtest` block use defaults (0 slippage, 0 commission,
full capital) so tests stay stable.

---

## Correctness Rules (invariants)

These must hold after Phase 3 and be covered by tests:

1. **D-14:** Signal entry/exit never uses the signal bar's close as fill price.
2. **No look-ahead on indicators:** ATR at signal bar uses only data through bar N.
3. **Conservation of cash:** equity = cash + marked position value each bar.
4. **Costs reduce equity:** commission and slippage never increase PnL.
5. **Determinism:** same candles + signals + config → identical trades and metrics.
6. **Forced close:** open position at last bar → `forced_close=True`, noted in output.
7. **Warmup:** signal `False` when indicators NaN (evaluator already handles).
8. **Complete position close (D-47):** every exit sells/closes 100% of the open lot — no partial exits.
9. **risk_pct (D-51):** requires `stop_loss`; invalid config fails at startup.

---

## Build Order

Each step is independently verifiable.

### Step 0 — Q&A gate

**Complete.** D-37 through D-49 recorded in [DECISIONS.md](DECISIONS.md).

---

### Step 1 — Types and config

**Build**

- Extend `signals/types.py` for new stop/TP/sizing types.
- Add `backtest` section parsing in `config.py`.
- Extend `BacktestMetrics` and `Trade` (size, commission fields).

**Verify**

```bash
pytest tests/config/ -q
```

---

### Step 2 — Slippage and commission

**Build**

- `FillModel` / `CostModel` in `engine.py` or `backtest/fills.py`.
- Apply to signal fills and intrabar risk fills.

**Verify**

- Unit tests: long entry with 10 bps slippage raises fill above open.
- Commission reduces final capital vs zero-fee baseline.

---

### Step 3 — Position sizing

**Build**

- `full_capital` (default), `fixed_pct`, `fixed_notional`, `risk_pct`.
- Cash tracking separate from mark-to-market equity.

**Verify**

- `fixed_pct: 0.5` leaves ~50% cash uninvested on entry.
- `risk_pct` size scales inversely with ATR stop distance.

---

### Step 4 — Stop / take profit extensions

**Build**

- Fixed price stop and take profit.
- Trailing stop (`atr_trail`, `fixed_pct_trail`).
- `exit_reason` values: `trailing_stop`, `take_profit`, `stop_loss`, `signal`, `forced_close`.

**Verify**

- Trailing ratchet test: long trail moves up, never down.
- Fixed stop triggers at configured offset.

---

### Step 5 — Extended metrics + benchmark

**Build**

- `backtest/benchmark.py` — buy-and-hold equity from `close`.
- Sharpe, Sortino, Calmar, profit factor in `compute_metrics()`.
- Resample equity to daily when needed (OQ-39).

**Verify**

```bash
pytest tests/backtest/test_metrics.py -q
```

---

### Step 6 — Trade export + CLI

**Build**

- `backtest/export.py` — CSV writer.
- `run_backtest.py` — print extended summary, write trades CSV.

**Verify**

- CSV row count matches trade count.
- Manual run on `rsi_mean_reversion` strategy.

---

### Step 7 — Documentation and sign-off

**Build**

- Phase 3 completion section in this doc.
- Update `ROADMAP.md`, `DECISIONS.md`, README backtest section.

**Verify**

- Full suite green.
- [Done Criteria](#done-criteria) checklist.

---

## Testing Strategy

| Layer | Requirement |
|---|---|
| Engine fills | D-14 next-bar open; slippage direction; short PnL sign |
| Risk exits | Stop before TP same bar; trailing ratchet; forced close |
| Sizing | Cash conservation; risk_pct formula regression |
| Costs | Commission on entry+exit; zero-fee backward compat |
| Metrics | Hand-calculated Sharpe on tiny equity series; profit factor |
| Benchmark | B&H return matches manual `(close[-1]/close[0])-1` |
| Export | CSV columns and dtypes |
| Integration | `run_backtest` path with mocked or fixture candles |
| Non-regression | Existing engine tests still pass with default config |

---

## Done Criteria

Phase 3 is complete when all of the following are true:

| # | Criterion | Status |
|---|---|---|
| 1 | D-37 through D-51 recorded in DECISIONS.md | [x] |
| 2 | Slippage and commission configurable and tested | [x] |
| 3 | All four sizing modes implemented | [x] |
| 4 | Fixed, ATR, and trailing stops + fixed and RR take profit | [x] |
| 5 | Long and short dual strategies work with costs and sizing | [x] |
| 6 | Sharpe, Sortino, Calmar, profit factor + benchmark in metrics output | [x] |
| 7 | Trades exported to CSV each run | [x] |
| 8 | D-14 invariant preserved; dedicated tests pass | [x] |
| 9 | `pytest` full suite passes | [x] (`317 passed`) |
| 10 | `python run_backtest.py` runs end-to-end on synced DB data | [x] |

---

## Phase 3 Completion Assessment

**Assessment date:** 2026-06-06  
**Rating:** **8.5 / 10**  
**Completion:** **100% for Phase 3 scope** (plus D-52 entry edge trigger, shipped during sign-off)

Phase 3 delivers a trustworthy simulation engine: realistic fills, four sizing modes,
full risk exits, extended metrics, benchmark comparison, and reproducible trade logs.
The bar loop remains in `engine.py` with extracted `fills`, `risk`, and `sizing`
modules — sufficient for Phase 3 without a separate `RiskManager` class.

### Evidence checked

| Check | Result | Notes |
|---|---|---|
| Full unit suite | Passing | `317 passed` |
| D-37 through D-51 in DECISIONS.md | Done | Plus D-52 (entry trigger) |
| Slippage + commission | Done | `backtest/fills.py`; `test_fills.py`, `test_engine_costs.py` |
| Four sizing modes | Done | `test_sizing.py` |
| Stop / TP / trailing | Done | `test_risk.py` |
| Extended metrics + benchmark | Done | `test_metrics.py`, `test_benchmark.py` |
| CSV export | Done | `test_export.py`; `run_backtest.py` writes `output/trades.csv` |
| D-14 next-bar open | Done | `test_engine.py` |
| Dual long/short | Done | `test_engine.py` short leg |
| Zero-fee test default | Done | Missing `backtest` block → 0 bps / 0 commission |
| Production defaults | Done | `config.yaml` → 5 bps, 0.1% commission |
| Entry churn mitigation | Done | D-52 `entry_trigger: edge` (default); `test_evaluator.py` |

### Rating breakdown

| Area | Score | Comment |
|---|---|---|
| Architecture alignment | 9/10 | Layering matches HLD; fills/risk/sizing extracted cleanly |
| Feature completeness | 10/10 | All in-scope ROADMAP items shipped; multi-position correctly deferred |
| Correctness / invariants | 9/10 | D-14, intrabar priority, cash conservation, D-51 startup validation |
| Test coverage | 9/10 | Unit tests per module + `test_run_backtest_integration.py` (mocked DB) |
| Documentation | 8/10 | HLD/ROADMAP/DECISIONS updated at sign-off; README refreshed |
| Operational realism | 8/10 | Fees + slippage + sizing work; strategies still need user tuning per TF |

### Known gaps (acceptable for Phase 3)

- **No live-DB integration test** — `test_run_backtest_integration.py` mocks `get_candles`; manual run still needed against TimescaleDB.
- **Global `backtest` block only** — per-strategy cost override not implemented (HLD noted as later).
- **Level-triggered exits** remain default; only **entries** support edge trigger (D-52).
- **Phase 7 alerts** may need separate edge/level policy (OQ-21 partially open).

### Completion verdict

Phase 3 is **complete**. Phase 4 (client API layer) can start without backtest engine changes.

---

## Resolved Q&A (2026-06-06)

| ID | Question | Your decision |
|---|---|---|
| D-38 / costs | Slippage + commission defaults | **5 bps**, **0.1%** per fill (tests stay 0) |
| OQ-16 / D-43 | Multiple positions | **C** — one position only; defer to Phase 7 |
| OQ-17 / D-42 | Benchmark | **Per strategy:** `symbol` or `none` |
| OQ-39 / D-46 | Sharpe on 1m data | **OK** — daily equity resample |
| OQ-40 / D-37 | Stop vs signal | **A** — intrabar stop/TP first |
| OQ-41 / D-49 | Long + short together | **A** — one net position |
| OQ-42 / D-41 | Trailing start | **B** — bar after entry |
| OQ-43 / D-47 | Complete position close | **100% of position** on every exit |
| OQ-43 / D-51 | risk_pct without stop | **ValueError** at startup |
| OQ-44 / D-48 | Scope | **A** — full Phase 3 |
| D-40 | Sizing modes | **All four** |
| D-41 | Trailing types | **Both** atr_trail + fixed_pct_trail |

### OQ-39 explained (D-46)

On **`1m`** backtests there are ~1,440 bars per day. If Sharpe uses every bar’s return,
tiny positive drift looks amazing statistically (autocorrelation). **Fix:** collapse equity
to **one value per UTC day**, compute daily returns, then annualize Sharpe/Sortino.
Does not change the trade simulation — only how risk metrics are reported.

---

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Scope creep (full exchange simulator) | Explicit out-of-scope list |
| Sharpe misleading on 1m data | Daily resample (OQ-39) |
| Trailing stop look-ahead | Trail uses only past bars' highs/lows |
| Config explosion | Global `backtest` defaults + per-side overrides only where needed |
| Pre-work drift (engine already extended) | HLD inventory table; tests lock behavior |
| Cash vs equity bugs with partial sizing | Conservation invariant + dedicated tests |

---

## Relationship to Later Phases

| Phase 3 output | Consumer |
|---|---|
| Trustworthy engine | Phase 5+ pattern backtests |
| Trade CSV | Phase 8 UI, AI post-trade analysis |
| Benchmark metrics | Phase 7 screener ranking |
| Risk sizing + ATR stops | Live-alert position sizing (future) |
| `max_positions` | Phase 7 multi-symbol portfolio (extend) |

Phase 3 must not change `get_candles()` (D-06) or the indicator registry contract (D-32).

---

## References

- [PHASE_2_HLD.md](PHASE_2_HLD.md) — indicator foundation (complete)
- [PHASE_1_HLD.md](PHASE_1_HLD.md) — data foundation
- [ROADMAP.md](ROADMAP.md) — Phase 3 feature list
- [DECISIONS.md](DECISIONS.md) — D-10, D-14, D-24
- [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) — OQ-16, OQ-17
- [POC_HLD.md](POC_HLD.md) — original engine scope
