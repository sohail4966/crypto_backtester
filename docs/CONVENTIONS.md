# Code Conventions

This document defines the rules every piece of code in this repository must follow.
These are not suggestions — they apply to all modules, all phases, from the POC onward.
When in doubt, refer here before writing or reviewing code.

---

## 1. Language & Formatting

- **Python 3.11+** only.
- **4 spaces** for indentation. No tabs.
- **Max line length: 100 characters.** Prefer shorter, but 100 is the hard limit.
- Use **f-strings** for string formatting. Not `.format()`, not `%`.
- Use **double quotes** for strings consistently. Single quotes only inside a string
  that already contains double quotes.
- One blank line between methods inside a class. Two blank lines between top-level
  definitions (classes, functions).
- All files end with a single newline character.

**Formatter:** `black` with `--line-length 100`.  
**Linter:** `ruff`.  
Run both before committing. Neither is optional.

---

## 2. Type Hints

Every function and method signature must have type hints — parameters and return type.
No exceptions.

```python
# correct
def sma(close: pd.Series, period: int) -> pd.Series:
    ...

# wrong — missing types
def sma(close, period):
    ...
```

- Use `pd.Series`, `pd.DataFrame` from pandas directly in hints.
- Use `Optional[X]` (or `X | None` in 3.10+ style) when a value may be absent.
- Use `dict[str, Any]` for untyped dicts only when the structure is genuinely variable.
  Prefer a `TypedDict` or dataclass when the shape is known.
- Return type must always be explicit. Never omit it, even for `-> None`.

---

## 3. Docstrings

Every **module**, **class**, and **function/method** must have a docstring.
No exceptions, even for short or "obvious" functions.

### Module docstring
First line of every `.py` file, before imports:
```python
"""
Indicator functions for computing technical analysis values from OHLCV data.
All functions are pure: they take a pandas Series and return a pandas Series.
"""
```

### Function docstring — use Google style
```python
def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """
    Compute RSI via TA-Lib wrapper.

    Args:
        close: Closing price series, indexed by datetime.
        period: Lookback period. Default is 14.

    Returns:
        RSI values as a float Series in the range [0, 100].
        First (period - 1) values are NaN.

    Raises:
        ValueError: If period is less than 2 or greater than len(close).
    """
```

### Class docstring
```python
class BacktestEngine:
    """
    Runs a long-only backtest against a candle DataFrame.

    Executes entries on the bar after the signal fires to avoid look-ahead bias.
    One position at a time. All sizing and fee logic is configurable via BacktestConfig.
    """
```

Rules:
- First line is a single sentence ending with a period. It must stand alone as a summary.
- Leave a blank line after the first sentence if there is more to say.
- Document **what** the function does and **why** any non-obvious choice was made.
  Do not document **how** — that is what the code is for.
- If a function has side effects (writes to DB, mutates state), say so explicitly.

---

## 4. Comments

Comments explain **intent and reasoning**, not mechanics.

```python
# correct — explains why, not what
# TA-Lib uses Wilder's smoothing for RSI (alpha = 1/period), not standard EMA.
alpha = 1 / period

# wrong — just restates the code
# Divide 1 by period to get alpha
alpha = 1 / period
```

**Add a comment when:**
- A formula or algorithm is non-obvious (include a reference if possible)
- A deliberate workaround or trade-off was made
- An edge case is being handled that is not obvious from the code
- A "why not X" decision is embedded in the code

**Do not add a comment when:**
- The code reads clearly on its own
- The docstring already covers it
- The comment would just repeat the variable or function name in prose

Use `# TODO:` for known gaps. Always include what the current limitation is and what
a full solution would require. Never leave a bare `# TODO` with no context.

```python
# TODO: This uses forward-fill for gaps which distorts volume metrics.
#       A proper solution would flag gaps and skip them in indicator calculations.
```

---

## 5. Design Principles

### KISS — Keep It Simple
Write the simplest thing that correctly solves the problem at hand.
Do not add abstraction, configurability, or generality until there is a concrete
second use case that requires it.

> If you are building it "just in case," stop.

### DRY — Don't Repeat Yourself
If the same logic appears twice, extract it. If it appears three times, it needs a
named function with a docstring.

### SOLID

**Single Responsibility**  
Each module, class, and function does one thing. A function that fetches data AND
computes an indicator AND writes to the DB violates this rule. Split it.

```
data/fetcher.py                    — fetches from exchange
data/db.py                         — opens connections only (no SQL)
data/migrations/sql/V*.sql         — versioned DDL (Flyway-style; applied on startup)
data/migrations/migrator.py        — runs pending migrations; records schema_migrations
data/repository/queries.py         — DML only (SELECT/INSERT/UPDATE)
data/repository/candle_repository.py — executes DML (like JPA @Repository + nativeQuery)
data/storage.py                    — calls migrator on startup; write facade → repository
data/loader.py                     — read facade → DataFrame (get_candles boundary)
```

**Migration rule:** Schema changes are new files `V004__add_column.sql`, never edits to
applied migrations. `run_migrations()` runs on application startup before reads/writes.

**Repository rule:** Do not put SQL in `storage.py`, `loader.py`, or business modules.
DDL → `data/migrations/sql/`. DML → `data/repository/queries.py` + repository method.

**Open/Closed**  
New indicators, patterns, and signal types should be addable without modifying
existing evaluator or engine code. Use registries and dispatch tables:
```python
INDICATORS: dict[str, Callable] = {
    "RSI": rsi,
    "SMA": sma,
}
# Adding a new indicator = one line here. Nothing else changes.
```

**Liskov Substitution**  
If there is a base class or protocol (e.g. `IndicatorFn`), every implementation
must be substitutable. Do not have a subclass that silently ignores a parameter or
returns a different shape.

**Interface Segregation**  
Do not force callers to depend on things they do not use. A function that only needs
a close price series should not require a full OHLCV DataFrame.

**Dependency Inversion**  
High-level modules (backtest engine) should not depend on low-level details
(specific DB driver, specific indicator library). Depend on abstractions:
- The backtest engine calls `get_candles()`, not `psycopg.connect().execute(...)`.
- The signal evaluator calls `INDICATORS[name](series, **params)`, not `ta.rsi(...)`.

---

## 6. Functions

- **One level of abstraction per function.** A function that does high-level
  orchestration should not also contain low-level detail. Extract the detail.
- **Max ~30 lines per function.** If it is longer, it is doing too much.
- **No side effects in pure functions.** Indicator functions must never write to
  disk, mutate global state, or make network calls.
- **Return early.** Use guard clauses at the top of functions to handle edge cases
  and invalid inputs. Avoid deeply nested `if` blocks.

```python
# correct — guard clause
def sma(close: pd.Series, period: int) -> pd.Series:
    if period < 1:
        raise ValueError(f"period must be >= 1, got {period}")
    if len(close) < period:
        raise ValueError(f"series length {len(close)} is shorter than period {period}")
    return close.rolling(period).mean()

# wrong — nested
def sma(close, period):
    if period >= 1:
        if len(close) >= period:
            return close.rolling(period).mean()
```

---

## 7. Naming

| Thing | Convention | Example |
|---|---|---|
| File | `snake_case.py` | `backtest_engine.py` |
| Folder | `snake_case/` | `indicators/` |
| Function | `snake_case` | `compute_rsi()` |
| Variable | `snake_case` | `close_series` |
| Class | `PascalCase` | `BacktestEngine` |
| Constant | `UPPER_SNAKE_CASE` | `DEFAULT_RSI_PERIOD = 14` |
| Type alias | `PascalCase` | `OHLCVFrame = pd.DataFrame` |

**Be specific.** `data` is a bad variable name. `candles`, `close_series`, `trade_log`
are good. The name should make the type and purpose obvious without reading the
surrounding code.

**Avoid abbreviations** except for universally understood ones:
- OK: `df`, `ts`, `ohlcv`, `sma`, `rsi`, `tf` (timeframe)
- Not OK: `d`, `s`, `calc`, `proc`, `mgr`, `util`

---

## 8. Error Handling

- **Raise specific exceptions** with messages that tell you exactly what went wrong
  and what was expected.
- Use built-in exception types where appropriate: `ValueError` for bad inputs,
  `KeyError` for missing dict keys, `FileNotFoundError` for missing files.
- Define custom exception classes for domain errors that callers need to catch
  specifically:

```python
class DataGapError(Exception):
    """Raised when expected candles are missing from the database."""

class InvalidSignalError(Exception):
    """Raised when a signal dict does not conform to the DSL schema."""
```

- Never use bare `except:` or `except Exception:` to swallow errors silently.
  If you catch an exception, either handle it meaningfully or re-raise it.
- Never use exceptions for control flow (do not raise an exception to signal a
  "not found" case that is expected — return `None` or an empty result instead).

---

## 9. Module Structure

Every module file follows this order:

```python
"""Module docstring."""

# 1. Standard library imports
import os
from datetime import datetime

# 2. Third-party imports
import pandas as pd
import psycopg

# 3. Internal imports
from data.loader import get_candles
from data.repository.candle_repository import CandleRepository
from indicators.talib_wrappers import rsi

# 4. Constants
DEFAULT_PERIOD = 14

# 5. Type aliases (if any)
OHLCVFrame = pd.DataFrame

# 6. Classes and functions
```

Group imports as above, separated by blank lines. Never mix standard library,
third-party, and internal imports in the same block.

---

## 10. Configuration

- **No hardcoded values** for anything that might change: DB connection strings,
  symbols, timeframes, periods, thresholds.
- Use a config file (`config.yaml` or `.env` for secrets) and load it at startup.
- Constants that are architectural (e.g. `ENTRY_ON_NEXT_BAR = True`) may live as
  module-level constants with a comment explaining why they exist.
- Never commit secrets (API keys, DB passwords) to the repository.
  Use `.env` + `python-dotenv`, and add `.env` to `.gitignore`.

---

## 11. Testing

- Every pure function (all indicators, signal evaluator, metrics) must have unit tests.
- Test files live in a `tests/` folder mirroring the module structure:
  `tests/indicators/test_basic.py` tests `indicators/basic.py`.
- Test function names follow `test_<what>_<condition>_<expected>`:
  `test_rsi_period_14_returns_series_aligned_to_close()`
- Each test has one assertion or one logical group of related assertions. Do not
  test three unrelated behaviors in one test.
- **Indicator tests (Phase 2+):** Verify param validation, warmup NaN behavior, index
  alignment, and synthetic hand-calculated cases. TA-Lib is the reference implementation
  (D-28) — TradingView cross-checks are not required.
- **POC historical note:** Phase 0 used TradingView RSI baselines (D-13); those tests
  are removed when POC custom indicators are replaced by TA-Lib wrappers.

---

## 12. Git

- **Commit messages** follow the format: `<type>: <short description>`
  - Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`
  - Example: `feat: add RSI indicator with Wilder's smoothing`
  - Example: `fix: correct look-ahead bias in backtest entry price`
- **One logical change per commit.** Do not bundle a bug fix and a new feature
  in the same commit.
- **Branch names:** `phase-N/<short-description>` — e.g. `phase-0/backtest-engine`
- Never commit directly to `main`. Every change goes through a branch.
- The `main` branch must always run. Do not merge broken code.

---

## 13. What to Always Avoid

| Anti-pattern | Why |
|---|---|
| Magic numbers inline | Use named constants with explanatory names |
| God functions (100+ lines doing everything) | Split by single responsibility |
| Mutable default arguments `def f(x=[])` | Classic Python gotcha; use `None` as default |
| `import *` | Makes it impossible to know where names come from |
| Silently catching all exceptions | Hides bugs; always handle or re-raise |
| Printing for debugging and leaving it in | Use `logging` module; never leave `print()` in committed code |
| Storing secrets in code | Use `.env` files; never commit API keys |
| Writing code "for the future" without a current need | YAGNI — You Aren't Gonna Need It |
