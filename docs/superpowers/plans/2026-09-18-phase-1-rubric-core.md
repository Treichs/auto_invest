# Phase 1 Rubric Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the trade rubric as plain, tested Python that knows nothing about any trading engine: input records, settlement ledger, cost model, position sizing, eight must-pass checks, five score components, and a decision record.

**Architecture:** One module per rubric stage inside `auto_invest.rubric`. Every input and output is a frozen dataclass; every rule is a plain function taking records plus a settings object and returning a record. The rubric never imports `auto_invest.settings` (it carries pydantic); it reads the attributes it needs from whatever settings object is passed in. Missing data fails a check or scores zero, never raises.

**Tech Stack:** Python 3.12, standard library only inside the rubric package (`dataclasses`, `datetime`, `zoneinfo`, `statistics`, `math`). pydantic in the settings loader. pytest. uv.

**Spec:** `docs/superpowers/specs/2026-09-18-phase-1-rubric-core-design.md`

## Global Constraints

- The rubric package imports only the standard library and its own modules; a test fails on `nautilus_trader`, `AlgorithmImports`, `QuantConnect`, `pandas`, `numpy`, or `auto_invest.settings` (spec R1.1).
- Every record is a frozen dataclass; every rubric function is pure: no file, clock, or network access (R1.2).
- `RUBRIC_VERSION` is a string exposed by the package (R1.3).
- Long only: a stop is always below the entry (R1.4).
- All timestamps are timezone-aware; time-of-day rules use `settings.timezone`, which is `America/New_York` (R1.5).
- Missing data fails with reason `missing: <Record>.<field>`; a function never raises on bad input.
- No loose comments in code. No file lists in documentation. Commit after every task with the message given.
- Run every command from the repo root `C:\Dev\Git\auto_invest`. `uv run pytest` is the test command.
- Never edit `config/ceilings.toml` except as Task 1 states; never push.

## File Structure

| Path | Responsibility |
|---|---|
| `src/auto_invest/settings.py` (modify) | Adds the nine Phase 1 settings and the "at least" ceiling direction |
| `config/settings.toml`, `config/ceilings.toml` (modify) | The nine placeholder values |
| `src/auto_invest/rubric/__init__.py` | `RUBRIC_VERSION` |
| `src/auto_invest/rubric/records.py` | The nine input records and `first_missing` |
| `src/auto_invest/rubric/settlement.py` | Settlement date, usable settled cash, combination with the broker figure |
| `src/auto_invest/rubric/costs.py` | IBKR tiered commission and spread cost |
| `src/auto_invest/rubric/sizing.py` | `Size` and `position_size` |
| `src/auto_invest/rubric/bars.py` | Time-of-day helpers over minute bars |
| `src/auto_invest/rubric/checks.py` | `CheckResult`, the eight checks, `run_checks` |
| `src/auto_invest/rubric/score.py` | `ComponentScore`, the five components, `SignalScore`, `signal_score` |
| `src/auto_invest/rubric/decision.py` | `DecisionRecord` and `decide` |
| `tests/conftest.py` | Shared builders: timestamps, minute bars, daily bars, history sessions, a loaded settings fixture |
| `tests/test_rubric_imports.py`, `tests/test_records.py`, `tests/test_settlement.py`, `tests/test_costs.py`, `tests/test_sizing.py`, `tests/test_bars.py`, `tests/test_checks.py`, `tests/test_score.py`, `tests/test_decision.py` | One test module per rubric module |

---

### Task 1: Phase 1 settings and ceiling directions

**Files:**
- Modify: `config/settings.toml`
- Modify: `config/ceilings.toml`
- Modify: `src/auto_invest/settings.py`
- Modify: `tests/test_settings.py`

**Interfaces:**
- Produces: `Settings` gains `quote_max_age_seconds: float`, `price_band: float`, `spread_cap: float`, `volume_floor: float`, `max_cost_fraction_of_risk: float`, `score_threshold: float`, `order_value_cap: float`, `opening_range_minutes: int`, `history_sessions: int`. `Ceilings` gains the first seven. Every later task reads these attributes by name.

- [ ] **Step 1: Write the failing tests**

Replace the `BASE` dictionary at the top of `tests/test_settings.py` and add the new parametrised cases:

```python
BASE = {
    "risk_per_trade": 0.005,
    "daily_loss_limit": 0.01,
    "per_symbol_cap": 0.25,
    "total_exposure_cap": 0.80,
    "entries_per_day": 3,
    "settled_cash_only": True,
    "no_leverage": True,
    "entry_window_start": "10:00",
    "entry_window_end": "15:30",
    "forced_close": "15:50",
    "quote_max_age_seconds": 5,
    "price_band": 0.10,
    "spread_cap": 0.0005,
    "volume_floor": 1000000,
    "max_cost_fraction_of_risk": 0.10,
    "score_threshold": 0.6,
    "order_value_cap": 0.25,
}
EXTRA = {
    "currency": "USD",
    "timezone": "America/New_York",
    "approved_symbols": ["SPY", "QQQ"],
    "opening_range_minutes": 5,
    "history_sessions": 20,
}
```

Add to `test_repo_config_files_load`:

```python
    assert settings.quote_max_age_seconds == 5
    assert settings.price_band == 0.10
    assert settings.spread_cap == 0.0005
    assert settings.volume_floor == 1000000
    assert settings.max_cost_fraction_of_risk == 0.10
    assert settings.score_threshold == 0.6
    assert settings.order_value_cap == 0.25
    assert settings.opening_range_minutes == 5
    assert settings.history_sessions == 20
```

Extend the parametrised list in `test_each_setting_over_its_ceiling_fails` with:

```python
        ("quote_max_age_seconds", 6),
        ("price_band", 0.11),
        ("spread_cap", 0.0006),
        ("volume_floor", 999999),
        ("max_cost_fraction_of_risk", 0.11),
        ("score_threshold", 0.59),
        ("order_value_cap", 0.26),
```

Add one more test:

```python
def test_tightened_phase_1_settings_pass():
    check_against_ceilings(
        settings_with(
            quote_max_age_seconds=2,
            price_band=0.05,
            spread_cap=0.0002,
            volume_floor=2000000,
            max_cost_fraction_of_risk=0.05,
            score_threshold=0.8,
            order_value_cap=0.10,
        ),
        ceilings(),
    )
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_settings.py -q`
Expected: FAIL with pydantic `ValidationError` mentioning `Extra inputs are not permitted` for `quote_max_age_seconds`.

- [ ] **Step 3: Add the values to both TOML files**

Append to `config/settings.toml`:

```toml

# Phase 1 placeholders. Unvalidated; Phase 2 research sets the real values.
quote_max_age_seconds = 5
price_band = 0.10
spread_cap = 0.0005
volume_floor = 1000000
max_cost_fraction_of_risk = 0.10
score_threshold = 0.6
order_value_cap = 0.25
opening_range_minutes = 5
history_sessions = 20
```

Append to `config/ceilings.toml`:

```toml

# Phase 1 placeholders. Unvalidated; Phase 2 research sets the real values.
quote_max_age_seconds = 5
price_band = 0.10
spread_cap = 0.0005
volume_floor = 1000000
max_cost_fraction_of_risk = 0.10
score_threshold = 0.6
order_value_cap = 0.25
```

- [ ] **Step 4: Extend the models and the ceiling check**

In `src/auto_invest/settings.py`, add these fields to `Limits` after `forced_close: time`:

```python
    quote_max_age_seconds: float = Field(gt=0)
    price_band: float = Field(gt=0, le=1)
    spread_cap: float = Field(gt=0, le=1)
    volume_floor: float = Field(ge=0)
    max_cost_fraction_of_risk: float = Field(gt=0, le=1)
    score_threshold: float = Field(ge=0, le=1)
    order_value_cap: float = Field(gt=0, le=1)
```

Add these to `Settings` after `approved_symbols`:

```python
    opening_range_minutes: int = Field(gt=0)
    history_sessions: int = Field(gt=0)
```

Replace the whole `check_against_ceilings` function with:

```python
def check_against_ceilings(settings: Settings, ceilings: Ceilings) -> None:
    at_most = [
        "risk_per_trade",
        "daily_loss_limit",
        "per_symbol_cap",
        "total_exposure_cap",
        "entries_per_day",
        "entry_window_end",
        "forced_close",
        "quote_max_age_seconds",
        "price_band",
        "spread_cap",
        "max_cost_fraction_of_risk",
        "order_value_cap",
    ]
    at_least = ["entry_window_start", "volume_floor", "score_threshold"]
    problems = []
    for name in at_most:
        if getattr(settings, name) > getattr(ceilings, name):
            problems.append(
                f"{name} = {getattr(settings, name)} exceeds ceiling {getattr(ceilings, name)}"
            )
    for name in at_least:
        if getattr(settings, name) < getattr(ceilings, name):
            problems.append(
                f"{name} = {getattr(settings, name)} is below ceiling {getattr(ceilings, name)}"
            )
    for flag in ("settled_cash_only", "no_leverage"):
        if not getattr(settings, flag):
            problems.append(f"{flag} must be true")
    if problems:
        raise CeilingExceeded("; ".join(problems))
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_settings.py -q`
Expected: all pass (27 tests).

- [ ] **Step 6: Commit**

```bash
git add config/settings.toml config/ceilings.toml src/auto_invest/settings.py tests/test_settings.py
git commit -m "feat: Phase 1 placeholder settings with ceiling directions"
```

---

### Task 2: Input records, rubric version, and the import guard

**Files:**
- Modify: `src/auto_invest/rubric/__init__.py`
- Create: `src/auto_invest/rubric/records.py`
- Create: `tests/conftest.py`
- Create: `tests/test_rubric_imports.py`
- Create: `tests/test_records.py`

**Interfaces:**
- Produces: records `Quote`, `Bar`, `InstrumentStatus`, `Position`, `AccountState`, `Sale`, `SettlementLedger`, `Candidate`, `MarketData` with the fields in spec B2; `first_missing(label: str, record, *names: str) -> str | None`; `RUBRIC_VERSION: str`. `conftest.py` builders `ts`, `minute_bars`, `daily_bars`, `history_bars`, `DAY`, `ET`, and the `settings` fixture, used by every later test module.

- [ ] **Step 1: Write the shared test builders**

Create `tests/conftest.py`:

```python
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from auto_invest.rubric.records import Bar
from auto_invest.settings import load_settings

ET = ZoneInfo("America/New_York")
DAY = date(2026, 9, 16)


def ts(hh: int, mm: int, day: date = DAY, ss: int = 0) -> datetime:
    return datetime.combine(day, time(hh, mm, ss), tzinfo=ET)


def minute_bars(
    day: date = DAY,
    start: time = time(9, 30),
    count: int = 390,
    open: float = 100.0,
    step: float = 0.0,
    volume: float = 10000.0,
    symbol: str = "SPY",
) -> tuple[Bar, ...]:
    bars = []
    price = open
    for i in range(count):
        start_at = datetime.combine(day, start, tzinfo=ET) + timedelta(minutes=i)
        close = price + step
        bars.append(
            Bar(symbol, start_at, price, max(price, close), min(price, close), close, volume)
        )
        price = close
    return tuple(bars)


def daily_bars(
    count: int = 260,
    end: date = DAY - timedelta(days=1),
    start_price: float = 100.0,
    step: float = 0.1,
    symbol: str = "SPY",
) -> tuple[Bar, ...]:
    bars = []
    day = end
    prices = [start_price + step * i for i in range(count)]
    days = []
    while len(days) < count:
        if day.weekday() < 5:
            days.append(day)
        day -= timedelta(days=1)
    for d, close in zip(reversed(days), prices):
        start_at = datetime.combine(d, time(9, 30), tzinfo=ET)
        bars.append(Bar(symbol, start_at, close, close, close, close, 1000000.0))
    return tuple(bars)


def history_bars(sessions: int = 20, before: date = DAY, **bar_kwargs) -> tuple[Bar, ...]:
    bars: list[Bar] = []
    day = before - timedelta(days=1)
    done = 0
    while done < sessions:
        if day.weekday() < 5:
            bars = list(minute_bars(day=day, **bar_kwargs)) + bars
            done += 1
        day -= timedelta(days=1)
    return tuple(bars)


@pytest.fixture
def settings():
    return load_settings()
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_rubric_imports.py`:

```python
import ast
import pathlib
import sys

import auto_invest.rubric

FORBIDDEN = {"nautilus_trader", "AlgorithmImports", "QuantConnect", "pandas", "numpy"}


def imported_names(path: pathlib.Path):
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name, 0
        elif isinstance(node, ast.ImportFrom):
            yield node.module or "", node.level


def test_rubric_imports_only_stdlib_and_itself():
    package = pathlib.Path(auto_invest.rubric.__file__).parent
    for path in package.glob("*.py"):
        for name, level in imported_names(path):
            top = name.split(".")[0]
            assert top not in FORBIDDEN, f"{path.name} imports {name}"
            assert top != "auto_invest" or name.startswith("auto_invest.rubric"), (
                f"{path.name} imports {name}"
            )
            assert level > 0 or top in sys.stdlib_module_names or name.startswith(
                "auto_invest.rubric"
            ), f"{path.name} imports {name}, which is not standard library"


def test_rubric_version_is_a_string():
    assert isinstance(auto_invest.rubric.RUBRIC_VERSION, str)
    assert auto_invest.rubric.RUBRIC_VERSION
```

Create `tests/test_records.py`:

```python
import json
from dataclasses import FrozenInstanceError, asdict

import pytest

from auto_invest.rubric.records import (
    AccountState,
    Candidate,
    Position,
    Quote,
    first_missing,
)
from conftest import ts


def test_records_are_frozen_and_hashable():
    quote = Quote("SPY", 100.0, 100.02, ts(10, 30))
    with pytest.raises(FrozenInstanceError):
        quote.bid = 1.0
    assert hash(quote) == hash(Quote("SPY", 100.0, 100.02, ts(10, 30)))
    assert quote == Quote("SPY", 100.0, 100.02, ts(10, 30))


def test_optional_defaults_only_where_the_spec_allows():
    position = Position("SPY", 1, 100.0)
    assert position.stop_price is None
    account = AccountState(5000.0, (), 0, 0.0, 0.0, True, True, ts(10, 30))
    assert account.settled_cash is None
    with pytest.raises(TypeError):
        Candidate("SPY", 100.0, 99.0)


def test_first_missing_names_the_record_and_field():
    assert first_missing("Quote", None, "bid") == "missing: Quote"
    quote = Quote("SPY", None, 100.02, ts(10, 30))
    assert first_missing("Quote", quote, "bid", "ask") == "missing: Quote.bid"
    assert first_missing("Quote", quote, "ask") is None


def test_records_serialise_to_json():
    account = AccountState(5000.0, (Position("SPY", 1, 100.0),), 0, 0.0, 0.0, True, True, None)
    assert json.loads(json.dumps(asdict(account)))["positions"][0]["symbol"] == "SPY"
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run pytest tests/test_rubric_imports.py tests/test_records.py -q`
Expected: FAIL with `ImportError` (no `records` module, no `RUBRIC_VERSION`).

- [ ] **Step 4: Write the records module and the version**

Replace `src/auto_invest/rubric/__init__.py` content with:

```python
RUBRIC_VERSION = "0.1.0"
```

Create `src/auto_invest/rubric/records.py`:

```python
from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class Quote:
    symbol: str | None
    bid: float | None
    ask: float | None
    timestamp: datetime | None


@dataclass(frozen=True)
class Bar:
    symbol: str | None
    start: datetime | None
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: float | None


@dataclass(frozen=True)
class InstrumentStatus:
    symbol: str | None
    listed_in_us: bool | None
    halted: bool | None


@dataclass(frozen=True)
class Position:
    symbol: str | None
    quantity: float | None
    average_price: float | None
    stop_price: float | None = None


@dataclass(frozen=True)
class AccountState:
    start_of_day_equity: float | None
    positions: tuple[Position, ...] | None
    entries_today: int | None
    realised_pnl_today: float | None
    unrealised_pnl_today: float | None
    broker_connected: bool | None
    positions_reconciled: bool | None
    timestamp: datetime | None
    settled_cash: float | None = None


@dataclass(frozen=True)
class Sale:
    trade_date: date | None
    proceeds: float | None


@dataclass(frozen=True)
class SettlementLedger:
    start_of_day_settled_cash: float | None
    buys_today: float | None
    sales: tuple[Sale, ...] | None


@dataclass(frozen=True)
class Candidate:
    symbol: str | None
    entry_price: float | None
    stop_price: float | None
    timestamp: datetime | None


@dataclass(frozen=True)
class MarketData:
    quote: Quote | None
    today_bars: tuple[Bar, ...] | None
    history_bars: tuple[Bar, ...] | None
    daily_bars: tuple[Bar, ...] | None


def first_missing(label: str, record, *names: str) -> str | None:
    if record is None:
        return f"missing: {label}"
    for name in names:
        if getattr(record, name) is None:
            return f"missing: {label}.{name}"
    return None
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_rubric_imports.py tests/test_records.py -q`
Expected: 6 passed.

- [ ] **Step 6: Commit**

```bash
git add src/auto_invest/rubric/__init__.py src/auto_invest/rubric/records.py tests/conftest.py tests/test_rubric_imports.py tests/test_records.py
git commit -m "feat: rubric input records, version, and import guard"
```

---

### Task 3: Settlement ledger

**Files:**
- Create: `src/auto_invest/rubric/settlement.py`
- Create: `tests/test_settlement.py`

**Interfaces:**
- Consumes: `Sale`, `SettlementLedger`, `AccountState`, `first_missing` from Task 2.
- Produces: `settlement_date(trade_date: date) -> date`; `usable_settled_cash(ledger: SettlementLedger | None, on_date: date) -> float | None`; `available_settled_cash(ledger, account: AccountState | None, on_date: date) -> float | None` (the lower of ledger and broker figures, spec R3.4).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_settlement.py`:

```python
from datetime import date

from auto_invest.rubric.records import AccountState, Sale, SettlementLedger
from auto_invest.rubric.settlement import (
    available_settled_cash,
    settlement_date,
    usable_settled_cash,
)

FRI = date(2026, 9, 11)
SAT = date(2026, 9, 12)
SUN = date(2026, 9, 13)
MON = date(2026, 9, 14)
TUE = date(2026, 9, 15)


def test_settlement_is_the_next_weekday():
    assert settlement_date(MON) == TUE
    assert settlement_date(FRI) == MON


def test_friday_sale_is_usable_from_monday():
    ledger = SettlementLedger(1000.0, 0.0, (Sale(FRI, 500.0),))
    assert usable_settled_cash(ledger, FRI) == 1000.0
    assert usable_settled_cash(ledger, SAT) == 1000.0
    assert usable_settled_cash(ledger, SUN) == 1000.0
    assert usable_settled_cash(ledger, MON) == 1500.0


def test_buys_today_reduce_usable_cash():
    ledger = SettlementLedger(1000.0, 400.0, ())
    assert usable_settled_cash(ledger, MON) == 600.0


def test_sales_with_missing_fields_are_ignored():
    ledger = SettlementLedger(1000.0, 0.0, (Sale(None, 500.0), Sale(FRI, None)))
    assert usable_settled_cash(ledger, TUE) == 1000.0


def test_missing_ledger_or_field_gives_none():
    assert usable_settled_cash(None, MON) is None
    assert usable_settled_cash(SettlementLedger(None, 0.0, ()), MON) is None
    assert usable_settled_cash(SettlementLedger(1000.0, None, ()), MON) is None


def account_with(settled_cash):
    return AccountState(5000.0, (), 0, 0.0, 0.0, True, True, None, settled_cash=settled_cash)


def test_available_is_the_lower_of_ledger_and_broker():
    ledger = SettlementLedger(1000.0, 0.0, ())
    assert available_settled_cash(ledger, account_with(800.0), MON) == 800.0
    assert available_settled_cash(ledger, account_with(1200.0), MON) == 1000.0
    assert available_settled_cash(ledger, account_with(None), MON) == 1000.0
    assert available_settled_cash(ledger, None, MON) == 1000.0
    assert available_settled_cash(None, account_with(800.0), MON) is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_settlement.py -q`
Expected: FAIL with `ModuleNotFoundError: auto_invest.rubric.settlement`.

- [ ] **Step 3: Write the settlement module**

Create `src/auto_invest/rubric/settlement.py`:

```python
from datetime import date, timedelta

from .records import AccountState, SettlementLedger, first_missing


def settlement_date(trade_date: date) -> date:
    settled = trade_date + timedelta(days=1)
    while settled.weekday() >= 5:
        settled += timedelta(days=1)
    return settled


def usable_settled_cash(ledger: SettlementLedger | None, on_date: date) -> float | None:
    if first_missing("SettlementLedger", ledger, "start_of_day_settled_cash", "buys_today"):
        return None
    settled = sum(
        sale.proceeds
        for sale in ledger.sales or ()
        if sale.trade_date is not None
        and sale.proceeds is not None
        and settlement_date(sale.trade_date) <= on_date
    )
    return ledger.start_of_day_settled_cash - ledger.buys_today + settled


def available_settled_cash(
    ledger: SettlementLedger | None, account: AccountState | None, on_date: date
) -> float | None:
    from_ledger = usable_settled_cash(ledger, on_date)
    if from_ledger is None:
        return None
    if account is None or account.settled_cash is None:
        return from_ledger
    return min(from_ledger, account.settled_cash)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_settlement.py -q`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/auto_invest/rubric/settlement.py tests/test_settlement.py
git commit -m "feat: settlement ledger with next-weekday settlement"
```

---

### Task 4: Cost model

**Files:**
- Create: `src/auto_invest/rubric/costs.py`
- Create: `tests/test_costs.py`

**Interfaces:**
- Consumes: `Quote` from Task 2.
- Produces: `commission_per_side(shares: int, price: float) -> float`; `round_trip_commission(shares, price) -> float`; `spread_cost_round_trip(shares: int, quote: Quote) -> float`; `total_cost_round_trip(shares: int, price: float, quote: Quote) -> float`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_costs.py`:

```python
import pytest

from auto_invest.rubric.costs import (
    commission_per_side,
    round_trip_commission,
    spread_cost_round_trip,
    total_cost_round_trip,
)
from auto_invest.rubric.records import Quote


def test_small_orders_pay_the_minimum():
    assert commission_per_side(2, 625.0) == pytest.approx(0.35)


def test_large_orders_pay_per_share():
    assert commission_per_side(200, 50.0) == pytest.approx(0.70)


def test_commission_is_capped_at_one_percent_of_value():
    assert commission_per_side(1, 1.0) == pytest.approx(0.01)


def test_zero_shares_cost_nothing():
    assert commission_per_side(0, 625.0) == 0.0


def test_round_trip_is_twice_one_side():
    assert round_trip_commission(2, 625.0) == pytest.approx(0.70)


def test_spread_cost_is_half_each_way():
    quote = Quote("SPY", 624.99, 625.00, None)
    assert spread_cost_round_trip(2, quote) == pytest.approx(0.02)


def test_worked_example_from_the_spec():
    quote = Quote("SPY", 624.99, 625.00, None)
    assert total_cost_round_trip(2, 625.0, quote) == pytest.approx(0.72)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_costs.py -q`
Expected: FAIL with `ModuleNotFoundError: auto_invest.rubric.costs`.

- [ ] **Step 3: Write the cost module**

Create `src/auto_invest/rubric/costs.py`:

```python
from .records import Quote

COMMISSION_PER_SHARE = 0.0035
COMMISSION_MINIMUM = 0.35
COMMISSION_CAP_OF_VALUE = 0.01


def commission_per_side(shares: int, price: float) -> float:
    if shares <= 0:
        return 0.0
    per_share = max(COMMISSION_PER_SHARE * shares, COMMISSION_MINIMUM)
    return min(per_share, COMMISSION_CAP_OF_VALUE * shares * price)


def round_trip_commission(shares: int, price: float) -> float:
    return 2 * commission_per_side(shares, price)


def spread_cost_round_trip(shares: int, quote: Quote) -> float:
    return shares * (quote.ask - quote.bid)


def total_cost_round_trip(shares: int, price: float, quote: Quote) -> float:
    return round_trip_commission(shares, price) + spread_cost_round_trip(shares, quote)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_costs.py -q`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add src/auto_invest/rubric/costs.py tests/test_costs.py
git commit -m "feat: IBKR tiered commission and spread cost model"
```

---

### Task 5: Position sizing with the $5,000 acceptance test

**Files:**
- Create: `src/auto_invest/rubric/sizing.py`
- Create: `tests/test_sizing.py`

**Interfaces:**
- Consumes: `Candidate`, `AccountState`, `Position`, `first_missing` from Task 2; settings attributes `risk_per_trade`, `per_symbol_cap`, `total_exposure_cap`.
- Produces: `Size(budget: float, shares: int, risk_at_budget: float, risk_at_shares: float, reason: str | None = None)`; `current_exposure(account: AccountState) -> float`; `position_size(candidate, account, usable_cash: float | None, settings) -> Size`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_sizing.py`:

```python
import pytest

from auto_invest.rubric.records import AccountState, Candidate, Position
from auto_invest.rubric.sizing import current_exposure, position_size
from conftest import ts


def account(equity=5000.0, positions=()):
    return AccountState(equity, positions, 0, 0.0, 0.0, True, True, ts(10, 30))


def candidate(entry, stop):
    return Candidate("SPY", entry, stop, ts(10, 30))


def test_blueprint_table_tight_stop(settings):
    size = position_size(candidate(100.0, 99.6), account(), 5000.0, settings)
    assert size.budget == pytest.approx(1250.0, abs=0.005)
    assert size.risk_at_budget == pytest.approx(5.0, abs=0.005)
    assert size.shares == 12


def test_blueprint_table_wide_stop(settings):
    size = position_size(candidate(100.0, 98.0), account(), 5000.0, settings)
    assert size.budget == pytest.approx(1250.0, abs=0.005)
    assert size.risk_at_budget == pytest.approx(25.0, abs=0.005)
    assert size.shares == 12


def test_whole_shares_at_a_real_price(settings):
    size = position_size(candidate(650.0, 647.4), account(), 5000.0, settings)
    assert size.budget == pytest.approx(1250.0, abs=0.005)
    assert size.shares == 1
    assert size.risk_at_shares == pytest.approx(2.6, abs=0.005)


def test_settled_cash_caps_the_budget(settings):
    size = position_size(candidate(100.0, 98.0), account(), 900.0, settings)
    assert size.budget == pytest.approx(900.0)
    assert size.shares == 9


def test_total_exposure_cap_leaves_room_only_for_the_rest(settings):
    held = (Position("QQQ", 30, 100.0),)
    size = position_size(candidate(100.0, 98.0), account(positions=held), 5000.0, settings)
    assert current_exposure(account(positions=held)) == 3000.0
    assert size.budget == pytest.approx(1000.0)


def test_budget_never_goes_below_zero(settings):
    held = (Position("QQQ", 50, 100.0),)
    size = position_size(candidate(100.0, 98.0), account(positions=held), 5000.0, settings)
    assert size.budget == 0.0
    assert size.shares == 0


def test_one_share_that_exactly_fits_is_not_lost_to_rounding(settings):
    size = position_size(candidate(1250.0, 1225.0), account(), 5000.0, settings)
    assert size.shares == 1


@pytest.mark.parametrize(
    "entry, stop, fragment",
    [(100.0, 100.0, "not below"), (100.0, 101.0, "not below"), (100.0, 0.0, "not below"), (0.0, -1.0, "not below")],
)
def test_bad_stop_gives_zero_shares_with_reason(settings, entry, stop, fragment):
    size = position_size(candidate(entry, stop), account(), 5000.0, settings)
    assert size.shares == 0
    assert fragment in size.reason


def test_missing_inputs_give_zero_shares_with_reason(settings):
    assert position_size(None, account(), 5000.0, settings).reason == "missing: Candidate"
    assert (
        position_size(candidate(100.0, None), account(), 5000.0, settings).reason
        == "missing: Candidate.stop_price"
    )
    assert (
        position_size(candidate(100.0, 98.0), account(equity=None), 5000.0, settings).reason
        == "missing: AccountState.start_of_day_equity"
    )
    assert (
        position_size(candidate(100.0, 98.0), account(positions=None), 5000.0, settings).reason
        == "missing: AccountState.positions"
    )
    assert (
        position_size(candidate(100.0, 98.0), account(), None, settings).reason
        == "missing: usable settled cash"
    )
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_sizing.py -q`
Expected: FAIL with `ModuleNotFoundError: auto_invest.rubric.sizing`.

- [ ] **Step 3: Write the sizing module**

Create `src/auto_invest/rubric/sizing.py`:

```python
import math
from dataclasses import dataclass

from .records import AccountState, Candidate, first_missing


@dataclass(frozen=True)
class Size:
    budget: float
    shares: int
    risk_at_budget: float
    risk_at_shares: float
    reason: str | None = None


NO_SIZE = Size(0.0, 0, 0.0, 0.0)


def current_exposure(account: AccountState) -> float:
    return sum(
        position.quantity * position.average_price
        for position in account.positions
        if position.quantity is not None and position.average_price is not None
    )


def position_size(
    candidate: Candidate | None,
    account: AccountState | None,
    usable_cash: float | None,
    settings,
) -> Size:
    reason = first_missing("Candidate", candidate, "entry_price", "stop_price") or first_missing(
        "AccountState", account, "start_of_day_equity", "positions"
    )
    if reason:
        return Size(0.0, 0, 0.0, 0.0, reason)
    if usable_cash is None:
        return Size(0.0, 0, 0.0, 0.0, "missing: usable settled cash")
    entry, stop = candidate.entry_price, candidate.stop_price
    if entry <= 0 or not 0 < stop < entry:
        return Size(0.0, 0, 0.0, 0.0, f"stop {stop} is not below entry {entry}")
    equity = account.start_of_day_equity
    stop_fraction = (entry - stop) / entry
    budget = min(
        settings.risk_per_trade * equity / stop_fraction,
        settings.per_symbol_cap * equity,
        settings.total_exposure_cap * equity - current_exposure(account),
        usable_cash,
    )
    budget = max(budget, 0.0)
    shares = math.floor(round(budget / entry, 9))
    return Size(budget, shares, budget * stop_fraction, shares * (entry - stop))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_sizing.py -q`
Expected: 12 passed.

- [ ] **Step 5: Commit**

```bash
git add src/auto_invest/rubric/sizing.py tests/test_sizing.py
git commit -m "feat: position sizing with whole shares and the \$5,000 acceptance test"
```

---

### Task 6: Time-of-day helpers over minute bars

**Files:**
- Create: `src/auto_invest/rubric/bars.py`
- Create: `tests/test_bars.py`

**Interfaces:**
- Consumes: `Bar` from Task 2; settings attribute `timezone`.
- Produces: `local(moment: datetime, timezone: str) -> datetime`; `bars_in_window(bars, start: time, end: time, timezone) -> tuple[Bar, ...]` (start inclusive, end exclusive, by local start time); `by_session(bars, timezone) -> dict[date, tuple[Bar, ...]]` (keys in date order); `volume_until(bars, until: time, timezone) -> float` (bars whose local start is before `until`); `complete(bars, *fields) -> bool` (True when non-empty and every named field is present on every bar).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_bars.py`:

```python
from datetime import date, time

from auto_invest.rubric.bars import bars_in_window, by_session, complete, local, volume_until
from auto_invest.rubric.records import Bar
from conftest import DAY, ET, history_bars, minute_bars, ts

TZ = "America/New_York"


def test_local_converts_to_eastern():
    utc_noon = ts(12, 0).astimezone(ET).astimezone(None)
    assert local(utc_noon, TZ).hour == 12


def test_first_half_hour_has_thirty_bars():
    window = bars_in_window(minute_bars(), time(9, 30), time(10, 0), TZ)
    assert len(window) == 30
    assert window[0].start == ts(9, 30)
    assert window[-1].start == ts(9, 59)


def test_by_session_groups_and_orders_by_date():
    sessions = by_session(history_bars(sessions=3), TZ)
    assert list(sessions) == sorted(sessions)
    assert len(sessions) == 3
    assert all(len(bars) == 390 for bars in sessions.values())
    assert all(day < DAY for day in sessions)


def test_volume_until_sums_bars_before_the_time():
    assert volume_until(minute_bars(volume=100.0), time(10, 0), TZ) == 3000.0
    assert volume_until((), time(10, 0), TZ) == 0.0


def test_complete_requires_every_field_on_every_bar():
    bars = minute_bars(count=2)
    assert complete(bars, "open", "close")
    assert not complete((), "open")
    broken = bars + (Bar("SPY", ts(9, 32), None, 1.0, 1.0, 1.0, 1.0),)
    assert not complete(broken, "open")
    assert complete(broken, "close")


def test_bars_without_a_start_are_skipped():
    bars = (Bar("SPY", None, 1.0, 1.0, 1.0, 1.0, 5.0),) + minute_bars(count=1)
    assert len(bars_in_window(bars, time(9, 30), time(10, 0), TZ)) == 1
    assert volume_until(bars, time(10, 0), TZ) == 10000.0
    assert list(by_session(bars, TZ)) == [date(2026, 9, 16)]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_bars.py -q`
Expected: FAIL with `ModuleNotFoundError: auto_invest.rubric.bars`.

- [ ] **Step 3: Write the bars module**

Create `src/auto_invest/rubric/bars.py`:

```python
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from .records import Bar


def local(moment: datetime, timezone: str) -> datetime:
    return moment.astimezone(ZoneInfo(timezone))


def bars_in_window(bars, start: time, end: time, timezone: str) -> tuple[Bar, ...]:
    return tuple(
        bar
        for bar in bars or ()
        if bar.start is not None and start <= local(bar.start, timezone).time() < end
    )


def by_session(bars, timezone: str) -> dict[date, tuple[Bar, ...]]:
    grouped: dict[date, list[Bar]] = {}
    for bar in bars or ():
        if bar.start is None:
            continue
        grouped.setdefault(local(bar.start, timezone).date(), []).append(bar)
    return {day: tuple(grouped[day]) for day in sorted(grouped)}


def volume_until(bars, until: time, timezone: str) -> float:
    return sum(
        bar.volume
        for bar in bars or ()
        if bar.start is not None
        and bar.volume is not None
        and local(bar.start, timezone).time() < until
    )


def complete(bars, *fields: str) -> bool:
    if not bars:
        return False
    return all(getattr(bar, field) is not None for bar in bars for field in fields)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_bars.py -q`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/auto_invest/rubric/bars.py tests/test_bars.py
git commit -m "feat: time-of-day helpers over minute bars"
```

---

### Task 7: Checks 1 to 3, data is sane, instrument is eligible, market is liquid

**Files:**
- Create: `src/auto_invest/rubric/checks.py`
- Create: `tests/test_checks.py`

**Interfaces:**
- Consumes: records and `first_missing` (Task 2); `volume_until`, `local` (Task 6); settings attributes `quote_max_age_seconds`, `price_band`, `approved_symbols`, `spread_cap`, `volume_floor`, `timezone`.
- Produces: `CheckResult(name: str, passed: bool, reason: str)`; `data_is_sane(candidate, market, settings) -> CheckResult`; `instrument_is_eligible(instrument, settings) -> CheckResult`; `market_is_liquid(candidate, market, settings) -> CheckResult`. Task 8 adds the other five and `run_checks` to this same module.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_checks.py`:

```python
import pytest

from auto_invest.rubric.checks import (
    data_is_sane,
    instrument_is_eligible,
    market_is_liquid,
)
from auto_invest.rubric.records import Candidate, InstrumentStatus, MarketData, Quote
from conftest import daily_bars, minute_bars, ts


def quote(bid=99.99, ask=100.01, at=None):
    return Quote("SPY", bid, ask, at or ts(10, 30))


def market(
    q=quote(),
    today=minute_bars(count=61, volume=20000.0),
    history=(),
    daily=daily_bars(step=0.0),
):
    return MarketData(q, today, history, daily)


def candidate(at=None):
    return Candidate("SPY", 100.0, 98.0, at or ts(10, 30))


def test_data_is_sane_passes_on_a_fresh_quote_near_the_close(settings):
    result = data_is_sane(candidate(), market(), settings)
    assert result.passed
    assert "within" in result.reason


def test_data_is_sane_fails_on_a_stale_quote(settings):
    result = data_is_sane(candidate(), market(q=quote(at=ts(10, 29, ss=50))), settings)
    assert not result.passed
    assert "10.0s old" in result.reason


def test_data_is_sane_fails_on_a_crossed_or_zero_market(settings):
    assert not data_is_sane(candidate(), market(q=quote(bid=100.02)), settings).passed
    assert not data_is_sane(candidate(), market(q=quote(bid=0.0)), settings).passed


def test_data_is_sane_fails_outside_the_price_band(settings):
    far = daily_bars(start_price=50.0, step=0.0)
    result = data_is_sane(candidate(), market(daily=far), settings)
    assert not result.passed
    assert "outside" in result.reason


@pytest.mark.parametrize(
    "c, m, expected",
    [
        (None, market(), "missing: Candidate"),
        (Candidate("SPY", 100.0, 98.0, None), market(), "missing: Candidate.timestamp"),
        (candidate(), None, "missing: MarketData"),
        (candidate(), market(q=Quote("SPY", None, 100.01, ts(10, 30))), "missing: Quote.bid"),
        (candidate(), market(q=Quote("SPY", 99.99, 100.01, None)), "missing: Quote.timestamp"),
        (candidate(), market(daily=()), "missing: MarketData.daily_bars"),
    ],
)
def test_data_is_sane_fails_when_data_is_missing(settings, c, m, expected):
    result = data_is_sane(c, m, settings)
    assert not result.passed
    assert result.reason == expected


def test_instrument_is_eligible_passes_for_an_approved_us_symbol(settings):
    assert instrument_is_eligible(InstrumentStatus("SPY", True, False), settings).passed


@pytest.mark.parametrize(
    "status, fragment",
    [
        (InstrumentStatus("SPY", False, False), "not US-listed"),
        (InstrumentStatus("SPY", True, True), "halted"),
        (InstrumentStatus("IWM", True, False), "not on the approved list"),
        (None, "missing: InstrumentStatus"),
        (InstrumentStatus("SPY", None, False), "missing: InstrumentStatus.listed_in_us"),
    ],
)
def test_instrument_is_eligible_fails(settings, status, fragment):
    result = instrument_is_eligible(status, settings)
    assert not result.passed
    assert fragment in result.reason


def test_market_is_liquid_passes_on_a_tight_spread_and_volume(settings):
    result = market_is_liquid(candidate(), market(), settings)
    assert result.passed


def test_market_is_liquid_fails_on_a_wide_spread(settings):
    result = market_is_liquid(candidate(), market(q=quote(bid=99.90, ask=100.10)), settings)
    assert not result.passed
    assert "spread" in result.reason


def test_market_is_liquid_fails_on_thin_volume(settings):
    result = market_is_liquid(candidate(), market(today=minute_bars(count=61, volume=10.0)), settings)
    assert not result.passed
    assert "volume" in result.reason


def test_market_is_liquid_counts_volume_only_before_the_candidate(settings):
    early = candidate(at=ts(9, 31))
    result = market_is_liquid(early, market(q=quote(at=ts(9, 31))), settings)
    assert not result.passed


@pytest.mark.parametrize(
    "c, m, expected",
    [
        (candidate(), market(today=()), "missing: MarketData.today_bars"),
        (candidate(), market(q=None), "missing: MarketData.quote"),
        (Candidate("SPY", 100.0, 98.0, None), market(), "missing: Candidate.timestamp"),
    ],
)
def test_market_is_liquid_fails_when_data_is_missing(settings, c, m, expected):
    result = market_is_liquid(c, m, settings)
    assert not result.passed
    assert result.reason == expected
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_checks.py -q`
Expected: FAIL with `ModuleNotFoundError: auto_invest.rubric.checks`.

- [ ] **Step 3: Write the first three checks**

Create `src/auto_invest/rubric/checks.py`:

```python
from dataclasses import dataclass

from .bars import local, volume_until
from .records import Candidate, InstrumentStatus, MarketData, first_missing


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    reason: str


def _quote_missing(market: MarketData | None) -> str | None:
    return first_missing("MarketData", market, "quote") or first_missing(
        "Quote", market.quote, "bid", "ask", "timestamp"
    )


def data_is_sane(candidate: Candidate | None, market: MarketData | None, settings) -> CheckResult:
    name = "data_is_sane"
    reason = first_missing("Candidate", candidate, "timestamp") or _quote_missing(market)
    if reason:
        return CheckResult(name, False, reason)
    if not market.daily_bars:
        return CheckResult(name, False, "missing: MarketData.daily_bars")
    last_close = market.daily_bars[-1].close
    if last_close is None:
        return CheckResult(name, False, "missing: Bar.close")
    quote = market.quote
    age = (candidate.timestamp - quote.timestamp).total_seconds()
    if age > settings.quote_max_age_seconds:
        return CheckResult(
            name, False, f"quote is {age:.1f}s old, limit {settings.quote_max_age_seconds}s"
        )
    if quote.bid <= 0 or quote.ask < quote.bid:
        return CheckResult(name, False, f"bid {quote.bid} and ask {quote.ask} are not a valid market")
    mid = (quote.bid + quote.ask) / 2
    band = settings.price_band
    if abs(mid / last_close - 1) > band:
        return CheckResult(
            name, False, f"mid {mid:.2f} is outside ±{band:.0%} of last close {last_close:.2f}"
        )
    return CheckResult(
        name, True, f"quote {age:.1f}s old, mid {mid:.2f} within ±{band:.0%} of {last_close:.2f}"
    )


def instrument_is_eligible(instrument: InstrumentStatus | None, settings) -> CheckResult:
    name = "instrument_is_eligible"
    reason = first_missing("InstrumentStatus", instrument, "symbol", "listed_in_us", "halted")
    if reason:
        return CheckResult(name, False, reason)
    if not instrument.listed_in_us:
        return CheckResult(name, False, f"{instrument.symbol} is not US-listed")
    if instrument.halted:
        return CheckResult(name, False, f"{instrument.symbol} is halted")
    if instrument.symbol not in settings.approved_symbols:
        return CheckResult(name, False, f"{instrument.symbol} is not on the approved list")
    return CheckResult(name, True, f"{instrument.symbol} is US-listed, trading, and approved")


def market_is_liquid(candidate: Candidate | None, market: MarketData | None, settings) -> CheckResult:
    name = "market_is_liquid"
    reason = first_missing("Candidate", candidate, "timestamp") or _quote_missing(market)
    if reason:
        return CheckResult(name, False, reason)
    if not market.today_bars:
        return CheckResult(name, False, "missing: MarketData.today_bars")
    quote = market.quote
    mid = (quote.bid + quote.ask) / 2
    spread = (quote.ask - quote.bid) / mid
    if spread > settings.spread_cap:
        return CheckResult(name, False, f"spread {spread:.4%} is over the cap {settings.spread_cap:.4%}")
    until = local(candidate.timestamp, settings.timezone).time()
    volume = volume_until(market.today_bars, until, settings.timezone)
    if volume < settings.volume_floor:
        return CheckResult(
            name, False, f"volume {volume:,.0f} so far is under the floor {settings.volume_floor:,.0f}"
        )
    return CheckResult(name, True, f"spread {spread:.4%}, volume {volume:,.0f} so far")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_checks.py -q`
Expected: 23 passed. The records are frozen, so building the default `quote`, bars, and daily bars once at import time and sharing them between tests is safe.

- [ ] **Step 5: Commit**

```bash
git add src/auto_invest/rubric/checks.py tests/test_checks.py
git commit -m "feat: data sanity, eligibility, and liquidity checks"
```

---

### Task 8: Checks 4 to 8 and `run_checks`

**Files:**
- Modify: `src/auto_invest/rubric/checks.py`
- Modify: `tests/test_checks.py`

**Interfaces:**
- Consumes: `Size` (Task 5), `total_cost_round_trip` (Task 4), `current_exposure` (Task 5), `local` (Task 6); settings attributes `max_cost_fraction_of_risk`, `order_value_cap`, `per_symbol_cap`, `total_exposure_cap`, `entries_per_day`, `daily_loss_limit`, `entry_window_start`, `entry_window_end`, `timezone`.
- Produces: `trade_beats_its_costs(size, candidate, market, settings)`; `exit_is_defined(candidate, settings)`; `risk_budget_has_room(size, candidate, account, usable_cash, settings)`; `daily_loss_limit_not_hit(account, settings)`; `system_is_healthy(candidate, account, settings)`; `CHECK_NAMES: tuple[str, ...]` in blueprint order; `run_checks(candidate, market, instrument, account, usable_cash, size, settings) -> tuple[CheckResult, ...]` (always eight, blueprint order).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_checks.py` (extend the import block to include `CHECK_NAMES, daily_loss_limit_not_hit, exit_is_defined, risk_budget_has_room, run_checks, system_is_healthy, trade_beats_its_costs` from `auto_invest.rubric.checks`, and `AccountState, Position` from records, and `Size` from `auto_invest.rubric.sizing`):

```python
def account(equity=5000.0, positions=(), entries=0, realised=0.0, unrealised=0.0, connected=True, reconciled=True):
    return AccountState(equity, positions, entries, realised, unrealised, connected, reconciled, ts(10, 30))


def size(shares=12, budget=1250.0, risk_at_shares=24.0):
    return Size(budget, shares, budget * 0.02, risk_at_shares)


def test_trade_beats_its_costs_blueprint_wide_stop_passes(settings):
    two_shares = Size(1250.0, 2, 25.0, 25.0)
    result = trade_beats_its_costs(two_shares, Candidate("SPY", 625.0, 612.5, ts(10, 30)), market(q=quote(624.99, 625.00)), settings)
    assert result.passed
    assert "2.9%" in result.reason


def test_trade_beats_its_costs_blueprint_tight_stop_fails(settings):
    two_shares = Size(1250.0, 2, 5.0, 5.0)
    result = trade_beats_its_costs(two_shares, Candidate("SPY", 625.0, 622.5, ts(10, 30)), market(q=quote(624.99, 625.00)), settings)
    assert not result.passed
    assert "14.4%" in result.reason


def test_trade_beats_its_costs_fails_with_no_shares_or_no_risk(settings):
    assert not trade_beats_its_costs(size(shares=0), candidate(), market(), settings).passed
    assert not trade_beats_its_costs(size(risk_at_shares=0.0), candidate(), market(), settings).passed


def test_trade_beats_its_costs_fails_when_data_is_missing(settings):
    assert trade_beats_its_costs(None, candidate(), market(), settings).reason == "missing: Size"
    assert trade_beats_its_costs(size(), candidate(), market(q=None), settings).reason == "missing: MarketData.quote"
    assert trade_beats_its_costs(size(), None, market(), settings).reason == "missing: Candidate"


def test_exit_is_defined(settings):
    assert exit_is_defined(candidate(), settings).passed
    assert not exit_is_defined(Candidate("SPY", 100.0, 100.0, ts(10, 30)), settings).passed
    assert not exit_is_defined(Candidate("SPY", 100.0, 101.0, ts(10, 30)), settings).passed
    assert not exit_is_defined(Candidate("SPY", 100.0, 0.0, ts(10, 30)), settings).passed
    assert exit_is_defined(Candidate("SPY", 100.0, None, ts(10, 30)), settings).reason == "missing: Candidate.stop_price"
    assert exit_is_defined(None, settings).reason == "missing: Candidate"


def test_risk_budget_has_room_passes_inside_every_limit(settings):
    result = risk_budget_has_room(size(), candidate(), account(), 5000.0, settings)
    assert result.passed


@pytest.mark.parametrize(
    "s, acct, cash, fragment",
    [
        (size(shares=13), account(), 5000.0, "order value cap"),
        (size(shares=12), account(positions=(Position("QQQ", 30, 100.0),)), 5000.0, "total exposure"),
        (size(), account(entries=3), 5000.0, "entries today"),
        (size(), account(), 1199.0, "settled cash"),
        (size(shares=0), account(), 5000.0, "no shares"),
    ],
)
def test_risk_budget_has_room_fails_each_limit(settings, s, acct, cash, fragment):
    result = risk_budget_has_room(s, candidate(), acct, cash, settings)
    assert not result.passed
    assert fragment in result.reason


def test_risk_budget_per_symbol_cap_uses_its_own_name(settings):
    tight = settings.model_copy(update={"order_value_cap": 0.5})
    result = risk_budget_has_room(size(shares=13), candidate(), account(), 5000.0, tight)
    assert not result.passed
    assert "per-symbol cap" in result.reason


def test_risk_budget_has_room_fails_when_data_is_missing(settings):
    assert risk_budget_has_room(None, candidate(), account(), 5000.0, settings).reason == "missing: Size"
    assert risk_budget_has_room(size(), candidate(), account(entries=None), 5000.0, settings).reason == "missing: AccountState.entries_today"
    assert risk_budget_has_room(size(), candidate(), account(), None, settings).reason == "missing: usable settled cash"
    assert risk_budget_has_room(size(), Candidate("SPY", None, 98.0, ts(10, 30)), account(), 5000.0, settings).reason == "missing: Candidate.entry_price"


def test_daily_loss_limit(settings):
    assert daily_loss_limit_not_hit(account(realised=-20.0, unrealised=-29.0), settings).passed
    at_limit = daily_loss_limit_not_hit(account(realised=-25.0, unrealised=-25.0), settings)
    assert not at_limit.passed
    assert "-50.00" in at_limit.reason
    assert not daily_loss_limit_not_hit(account(realised=-60.0), settings).passed
    assert daily_loss_limit_not_hit(account(realised=None), settings).reason == "missing: AccountState.realised_pnl_today"
    assert daily_loss_limit_not_hit(None, settings).reason == "missing: AccountState"


def test_system_is_healthy_passes(settings):
    assert system_is_healthy(candidate(), account(), settings).passed


@pytest.mark.parametrize(
    "c, acct, fragment",
    [
        (candidate(), account(connected=False), "broker not connected"),
        (candidate(), account(reconciled=False), "positions not reconciled"),
        (candidate(), account(positions=(Position("SPY", 1, 100.0),)), "already holding SPY"),
        (candidate(at=ts(9, 59)), account(), "outside the entry window"),
        (candidate(at=ts(15, 30)), account(), "outside the entry window"),
        (None, account(), "missing: Candidate"),
        (candidate(), account(connected=None), "missing: AccountState.broker_connected"),
        (candidate(), account(positions=None), "missing: AccountState.positions"),
    ],
)
def test_system_is_healthy_fails_and_names_the_clause(settings, c, acct, fragment):
    result = system_is_healthy(c, acct, settings)
    assert not result.passed
    assert fragment in result.reason


def test_run_checks_returns_all_eight_in_blueprint_order(settings):
    results = run_checks(candidate(), market(), InstrumentStatus("SPY", True, False), account(), 5000.0, size(), settings)
    assert tuple(r.name for r in results) == CHECK_NAMES
    assert CHECK_NAMES == (
        "data_is_sane",
        "instrument_is_eligible",
        "market_is_liquid",
        "trade_beats_its_costs",
        "exit_is_defined",
        "risk_budget_has_room",
        "daily_loss_limit_not_hit",
        "system_is_healthy",
    )
    assert all(r.passed for r in results)


def test_run_checks_evaluates_every_check_even_after_a_failure(settings):
    results = run_checks(None, None, None, None, None, None, settings)
    assert len(results) == 8
    assert not any(r.passed for r in results)
    assert all(r.reason.startswith("missing") for r in results)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_checks.py -q`
Expected: FAIL with `ImportError: cannot import name 'trade_beats_its_costs'`.

- [ ] **Step 3: Add the five checks and `run_checks`**

Extend the import block at the top of `src/auto_invest/rubric/checks.py` to:

```python
from dataclasses import dataclass

from .bars import local, volume_until
from .costs import total_cost_round_trip
from .records import AccountState, Candidate, InstrumentStatus, MarketData, first_missing
from .sizing import Size, current_exposure
```

Append to the module:

```python
def trade_beats_its_costs(
    size: Size | None, candidate: Candidate | None, market: MarketData | None, settings
) -> CheckResult:
    name = "trade_beats_its_costs"
    reason = (
        first_missing("Size", size)
        or first_missing("Candidate", candidate, "entry_price")
        or _quote_missing(market)
    )
    if reason:
        return CheckResult(name, False, reason)
    if size.shares < 1:
        return CheckResult(name, False, "no shares to trade")
    if size.risk_at_shares <= 0:
        return CheckResult(name, False, "no amount at risk")
    cost = total_cost_round_trip(size.shares, candidate.entry_price, market.quote)
    fraction = cost / size.risk_at_shares
    limit = settings.max_cost_fraction_of_risk
    verdict = fraction <= limit
    return CheckResult(
        name,
        verdict,
        f"round-trip cost {cost:.2f} is {fraction:.1%} of risk {size.risk_at_shares:.2f}, limit {limit:.0%}",
    )


def exit_is_defined(candidate: Candidate | None, settings) -> CheckResult:
    name = "exit_is_defined"
    reason = first_missing("Candidate", candidate, "entry_price", "stop_price")
    if reason:
        return CheckResult(name, False, reason)
    if not 0 < candidate.stop_price < candidate.entry_price:
        return CheckResult(
            name, False, f"stop {candidate.stop_price} is not below entry {candidate.entry_price}"
        )
    return CheckResult(name, True, f"stop {candidate.stop_price} below entry {candidate.entry_price}")


def risk_budget_has_room(
    size: Size | None,
    candidate: Candidate | None,
    account: AccountState | None,
    usable_cash: float | None,
    settings,
) -> CheckResult:
    name = "risk_budget_has_room"
    reason = (
        first_missing("Size", size)
        or first_missing("Candidate", candidate, "entry_price")
        or first_missing("AccountState", account, "start_of_day_equity", "positions", "entries_today")
    )
    if reason:
        return CheckResult(name, False, reason)
    if usable_cash is None:
        return CheckResult(name, False, "missing: usable settled cash")
    if size.shares < 1:
        return CheckResult(name, False, "no shares to trade")
    equity = account.start_of_day_equity
    order_value = size.shares * candidate.entry_price
    exposure = current_exposure(account)
    limits = [
        (order_value > settings.order_value_cap * equity, f"order value {order_value:.2f} is over the order value cap {settings.order_value_cap * equity:.2f}"),
        (order_value > settings.per_symbol_cap * equity, f"order value {order_value:.2f} is over the per-symbol cap {settings.per_symbol_cap * equity:.2f}"),
        (exposure + order_value > settings.total_exposure_cap * equity, f"exposure {exposure + order_value:.2f} would be over the total exposure cap {settings.total_exposure_cap * equity:.2f}"),
        (account.entries_today >= settings.entries_per_day, f"entries today {account.entries_today} has reached the cap {settings.entries_per_day}"),
        (order_value > usable_cash, f"order value {order_value:.2f} is over usable settled cash {usable_cash:.2f}"),
    ]
    for failed, message in limits:
        if failed:
            return CheckResult(name, False, message)
    return CheckResult(
        name,
        True,
        f"order value {order_value:.2f}, exposure after {exposure + order_value:.2f}, entry {account.entries_today + 1} of {settings.entries_per_day}, settled cash {usable_cash:.2f}",
    )


def daily_loss_limit_not_hit(account: AccountState | None, settings) -> CheckResult:
    name = "daily_loss_limit_not_hit"
    reason = first_missing(
        "AccountState", account, "start_of_day_equity", "realised_pnl_today", "unrealised_pnl_today"
    )
    if reason:
        return CheckResult(name, False, reason)
    pnl = account.realised_pnl_today + account.unrealised_pnl_today
    limit = -settings.daily_loss_limit * account.start_of_day_equity
    return CheckResult(
        name, pnl > limit, f"today's P&L {pnl:.2f} against the halt at {limit:.2f}"
    )


def system_is_healthy(candidate: Candidate | None, account: AccountState | None, settings) -> CheckResult:
    name = "system_is_healthy"
    reason = first_missing("Candidate", candidate, "symbol", "timestamp") or first_missing(
        "AccountState", account, "broker_connected", "positions_reconciled", "positions"
    )
    if reason:
        return CheckResult(name, False, reason)
    if not account.broker_connected:
        return CheckResult(name, False, "broker not connected")
    if not account.positions_reconciled:
        return CheckResult(name, False, "positions not reconciled with the broker")
    if any(p.symbol == candidate.symbol and p.quantity for p in account.positions):
        return CheckResult(name, False, f"already holding {candidate.symbol}")
    at = local(candidate.timestamp, settings.timezone).time()
    if not settings.entry_window_start <= at < settings.entry_window_end:
        return CheckResult(
            name,
            False,
            f"{at:%H:%M} is outside the entry window {settings.entry_window_start:%H:%M} to {settings.entry_window_end:%H:%M}",
        )
    return CheckResult(name, True, f"connected, reconciled, flat in {candidate.symbol}, {at:%H:%M} inside the window")


CHECK_NAMES = (
    "data_is_sane",
    "instrument_is_eligible",
    "market_is_liquid",
    "trade_beats_its_costs",
    "exit_is_defined",
    "risk_budget_has_room",
    "daily_loss_limit_not_hit",
    "system_is_healthy",
)


def run_checks(
    candidate, market, instrument, account, usable_cash, size, settings
) -> tuple[CheckResult, ...]:
    return (
        data_is_sane(candidate, market, settings),
        instrument_is_eligible(instrument, settings),
        market_is_liquid(candidate, market, settings),
        trade_beats_its_costs(size, candidate, market, settings),
        exit_is_defined(candidate, settings),
        risk_budget_has_room(size, candidate, account, usable_cash, settings),
        daily_loss_limit_not_hit(account, settings),
        system_is_healthy(candidate, account, settings),
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_checks.py -q`
Expected: 48 passed.

- [ ] **Step 5: Commit**

```bash
git add src/auto_invest/rubric/checks.py tests/test_checks.py
git commit -m "feat: cost, exit, risk budget, daily loss, and health checks"
```

---

### Task 9: Score components, trend direction, opening range breakout, relative volume

**Files:**
- Create: `src/auto_invest/rubric/score.py`
- Create: `tests/test_score.py`

**Interfaces:**
- Consumes: `MarketData`, `Candidate` (Task 2); `bars_in_window`, `by_session`, `volume_until`, `local`, `complete` (Task 6); settings `opening_range_minutes`, `history_sessions`, `timezone`.
- Produces: `ComponentScore(name: str, value: float, reason: str)`; `clip(x) -> float`; `recent_sessions(market, candidate, settings) -> tuple[tuple[Bar, ...], ...]` (the last `history_sessions` sessions before the candidate's date, or `()` when fewer exist); `trend_direction(market, settings)`, `opening_range_breakout(candidate, market, settings)`, `relative_volume(candidate, market, settings)`, each returning `ComponentScore`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_score.py`:

```python
from datetime import time

import pytest

from auto_invest.rubric.records import Bar, Candidate, MarketData, Quote
from auto_invest.rubric.score import (
    opening_range_breakout,
    relative_volume,
    trend_direction,
)
from conftest import daily_bars, history_bars, minute_bars, ts


def candidate(entry=100.0, at=None):
    return Candidate("SPY", entry, entry * 0.98, at or ts(10, 30))


def market(
    today=minute_bars(count=61),
    history=history_bars(),
    daily=daily_bars(),
):
    return MarketData(Quote("SPY", 99.99, 100.01, ts(10, 30)), today, history, daily)


def test_trend_direction_all_lookbacks_positive_scores_one(settings):
    result = trend_direction(market(daily=daily_bars(step=0.1)), settings)
    assert result.value == 1.0


def test_trend_direction_all_lookbacks_negative_scores_zero(settings):
    result = trend_direction(market(daily=daily_bars(step=-0.1)), settings)
    assert result.value == 0.0


def test_trend_direction_counts_positive_lookbacks(settings):
    falling_year = [110.0 - 10.0 * i / 189 for i in range(190)]
    rising_quarter = [100.0 + 0.01 * k for k in range(1, 64)]
    closes = falling_year + rising_quarter
    bars = tuple(
        Bar("SPY", b.start, c, c, c, c, 1.0) for b, c in zip(daily_bars(count=253), closes)
    )
    result = trend_direction(market(daily=bars), settings)
    assert result.value == 0.5
    assert "2 of 4" in result.reason


def test_trend_direction_needs_253_closes(settings):
    result = trend_direction(market(daily=daily_bars(count=252)), settings)
    assert result.value == 0.0
    assert "missing" in result.reason
    assert trend_direction(market(daily=()), settings).value == 0.0
    assert trend_direction(None, settings).reason == "missing: MarketData"


def test_opening_range_breakout_above_the_range_high_scores_one(settings):
    today = minute_bars(count=61, open=100.0, step=0.0)
    assert opening_range_breakout(candidate(entry=100.5), market(today=today), settings).value == 1.0
    assert opening_range_breakout(candidate(entry=100.0), market(today=today), settings).value == 0.0


def test_opening_range_breakout_needs_the_full_opening_range(settings):
    four_bars = minute_bars(count=4)
    result = opening_range_breakout(candidate(), market(today=four_bars), settings)
    assert result.value == 0.0
    assert "missing" in result.reason
    assert opening_range_breakout(None, market(), settings).reason == "missing: Candidate"


def test_relative_volume_twice_the_average_scores_one(settings):
    today = minute_bars(count=61, volume=20000.0)
    history = history_bars(volume=10000.0)
    result = relative_volume(candidate(), market(today=today, history=history), settings)
    assert result.value == 1.0


def test_relative_volume_equal_to_average_scores_half(settings):
    result = relative_volume(candidate(), market(), settings)
    assert result.value == pytest.approx(0.5)


def test_relative_volume_needs_twenty_history_sessions(settings):
    result = relative_volume(candidate(), market(history=history_bars(sessions=19)), settings)
    assert result.value == 0.0
    assert "missing" in result.reason
    assert relative_volume(candidate(), market(today=()), settings).reason == "missing: MarketData.today_bars"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_score.py -q`
Expected: FAIL with `ModuleNotFoundError: auto_invest.rubric.score`.

- [ ] **Step 3: Write the score module with three components**

Create `src/auto_invest/rubric/score.py`:

```python
from dataclasses import dataclass
from datetime import datetime, time, timedelta

from .bars import bars_in_window, by_session, complete, local, volume_until
from .records import Bar, Candidate, MarketData, first_missing

OPEN = time(9, 30)
FIRST_HALF_HOUR_END = time(10, 0)
LOOKBACKS = (21, 63, 126, 252)


@dataclass(frozen=True)
class ComponentScore:
    name: str
    value: float
    reason: str


def clip(value: float) -> float:
    return max(0.0, min(1.0, value))


def recent_sessions(
    market: MarketData | None, candidate: Candidate | None, settings
) -> tuple[tuple[Bar, ...], ...]:
    if market is None or candidate is None or candidate.timestamp is None:
        return ()
    today = local(candidate.timestamp, settings.timezone).date()
    sessions = by_session(market.history_bars, settings.timezone)
    before = [bars for day, bars in sessions.items() if day < today]
    if len(before) < settings.history_sessions:
        return ()
    return tuple(before[-settings.history_sessions :])


def trend_direction(market: MarketData | None, settings) -> ComponentScore:
    name = "trend_direction"
    reason = first_missing("MarketData", market)
    if reason:
        return ComponentScore(name, 0.0, reason)
    needed = max(LOOKBACKS) + 1
    if not market.daily_bars or len(market.daily_bars) < needed:
        return ComponentScore(name, 0.0, f"missing: MarketData.daily_bars needs {needed} closes")
    if not complete(market.daily_bars, "close"):
        return ComponentScore(name, 0.0, "missing: Bar.close")
    closes = [bar.close for bar in market.daily_bars]
    returns = [closes[-1] / closes[-1 - lookback] - 1 for lookback in LOOKBACKS]
    positive = sum(1 for r in returns if r > 0)
    return ComponentScore(
        name, positive / len(LOOKBACKS), f"{positive} of {len(LOOKBACKS)} lookbacks positive"
    )


def opening_range_breakout(
    candidate: Candidate | None, market: MarketData | None, settings
) -> ComponentScore:
    name = "opening_range_breakout"
    reason = first_missing("Candidate", candidate, "entry_price") or first_missing(
        "MarketData", market
    )
    if reason:
        return ComponentScore(name, 0.0, reason)
    minutes = settings.opening_range_minutes
    end = (datetime.combine(datetime.min, OPEN) + timedelta(minutes=minutes)).time()
    window = bars_in_window(market.today_bars, OPEN, end, settings.timezone)
    if len(window) != minutes or not complete(window, "high"):
        return ComponentScore(name, 0.0, f"missing: MarketData.today_bars needs the first {minutes} bars")
    range_high = max(bar.high for bar in window)
    broke_out = candidate.entry_price > range_high
    return ComponentScore(
        name, 1.0 if broke_out else 0.0, f"entry {candidate.entry_price} against opening range high {range_high}"
    )


def relative_volume(candidate: Candidate | None, market: MarketData | None, settings) -> ComponentScore:
    name = "relative_volume"
    reason = first_missing("Candidate", candidate, "timestamp") or first_missing("MarketData", market)
    if reason:
        return ComponentScore(name, 0.0, reason)
    if not market.today_bars:
        return ComponentScore(name, 0.0, "missing: MarketData.today_bars")
    sessions = recent_sessions(market, candidate, settings)
    if not sessions:
        return ComponentScore(
            name, 0.0, f"missing: MarketData.history_bars needs {settings.history_sessions} sessions"
        )
    until = local(candidate.timestamp, settings.timezone).time()
    today = volume_until(market.today_bars, until, settings.timezone)
    average = sum(volume_until(s, until, settings.timezone) for s in sessions) / len(sessions)
    if average <= 0:
        return ComponentScore(name, 0.0, "history has no volume in the window")
    rvol = today / average
    return ComponentScore(name, clip(rvol / 2), f"relative volume {rvol:.2f}")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_score.py -q`
Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add src/auto_invest/rubric/score.py tests/test_score.py
git commit -m "feat: trend, opening range breakout, and relative volume components"
```

---

### Task 10: Score components, intraday momentum and volatility and volume conditions, and the combined score

**Files:**
- Modify: `src/auto_invest/rubric/score.py`
- Modify: `tests/test_score.py`

**Interfaces:**
- Consumes: everything in Task 9; settings `score_threshold`.
- Produces: `first_half_hour(bars, settings) -> tuple[Bar, ...]`; `intraday_momentum(candidate, market, settings)`, `volatility_and_volume_conditions(candidate, market, settings)` returning `ComponentScore`; `SignalScore(components: tuple[ComponentScore, ...], value: float, threshold: float, passed: bool)`; `components(candidate, market, settings) -> tuple[ComponentScore, ...]` (five, in blueprint order); `signal_score(components, settings) -> SignalScore`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_score.py` (extend the imports to include `components, intraday_momentum, signal_score, volatility_and_volume_conditions, ComponentScore` from `auto_invest.rubric.score`, `DAY` from `conftest`, and `from datetime import timedelta`):

```python
def test_intraday_momentum_strong_positive_open_scores_one(settings):
    today = minute_bars(count=61, open=100.0, step=0.1)
    history = history_bars(open=100.0, step=0.01)
    result = intraday_momentum(candidate(), market(today=today, history=history), settings)
    assert result.value == 1.0


def test_intraday_momentum_strong_negative_open_scores_zero(settings):
    today = minute_bars(count=61, open=100.0, step=-0.1)
    history = history_bars(open=100.0, step=0.01)
    result = intraday_momentum(candidate(), market(today=today, history=history), settings)
    assert result.value == 0.0


def test_intraday_momentum_flat_open_scores_half(settings):
    today = minute_bars(count=61, open=100.0, step=0.0)
    history = history_bars(open=100.0, step=0.01)
    result = intraday_momentum(candidate(), market(today=today, history=history), settings)
    assert result.value == pytest.approx(0.5)


def test_intraday_momentum_with_no_history_dispersion(settings):
    flat_history = history_bars(open=100.0, step=0.0)
    up = intraday_momentum(candidate(), market(today=minute_bars(count=61, step=0.1), history=flat_history), settings)
    down = intraday_momentum(candidate(), market(today=minute_bars(count=61, step=-0.1), history=flat_history), settings)
    flat = intraday_momentum(candidate(), market(today=minute_bars(count=61, step=0.0), history=flat_history), settings)
    assert (up.value, down.value, flat.value) == (1.0, 0.0, 0.5)


def test_intraday_momentum_scales_by_history_dispersion(settings):
    calm = history_bars(sessions=10, before=DAY, open=100.0, step=0.01)
    lively = history_bars(sessions=10, before=DAY - timedelta(days=14), open=100.0, step=0.03)
    today = minute_bars(count=61, open=100.0, step=-0.005)
    result = intraday_momentum(candidate(), market(today=today, history=calm + lively), settings)
    assert result.value == pytest.approx(0.25, abs=0.01)


def test_intraday_momentum_needs_the_first_half_hour_and_history(settings):
    late = minute_bars(start=time(10, 0), count=30)
    result = intraday_momentum(candidate(), market(today=late), settings)
    assert result.value == 0.0
    assert "missing" in result.reason
    short = intraday_momentum(candidate(), market(history=history_bars(sessions=5)), settings)
    assert short.value == 0.0
    assert intraday_momentum(None, market(), settings).reason == "missing: Candidate"


def test_volatility_and_volume_twice_average_scores_one(settings):
    today = minute_bars(count=61, open=100.0, step=0.2, volume=20000.0)
    history = history_bars(open=100.0, step=0.1, volume=10000.0)
    result = volatility_and_volume_conditions(candidate(), market(today=today, history=history), settings)
    assert result.value == pytest.approx(1.0)


def test_volatility_and_volume_at_average_scores_half(settings):
    today = minute_bars(count=61, open=100.0, step=0.1, volume=10000.0)
    history = history_bars(open=100.0, step=0.1, volume=10000.0)
    result = volatility_and_volume_conditions(candidate(), market(today=today, history=history), settings)
    assert result.value == pytest.approx(0.5)


def test_volatility_and_volume_quiet_day_scores_low(settings):
    today = minute_bars(count=61, open=100.0, step=0.0, volume=0.0)
    history = history_bars(open=100.0, step=0.1, volume=10000.0)
    result = volatility_and_volume_conditions(candidate(), market(today=today, history=history), settings)
    assert result.value == 0.0


def test_volatility_and_volume_needs_data(settings):
    assert volatility_and_volume_conditions(candidate(), market(today=()), settings).value == 0.0
    result = volatility_and_volume_conditions(candidate(), market(history=()), settings)
    assert "missing" in result.reason
    assert volatility_and_volume_conditions(None, market(), settings).reason == "missing: Candidate"


def test_components_are_five_in_blueprint_order(settings):
    names = [c.name for c in components(candidate(), market(), settings)]
    assert names == [
        "trend_direction",
        "intraday_momentum",
        "volatility_and_volume_conditions",
        "opening_range_breakout",
        "relative_volume",
    ]


def test_signal_score_is_the_mean_against_the_threshold(settings):
    scored = tuple(ComponentScore(n, v, "") for n, v in zip("abcde", (1.0, 1.0, 1.0, 0.0, 0.0)))
    result = signal_score(scored, settings)
    assert result.value == pytest.approx(0.6)
    assert result.threshold == 0.6
    assert result.passed
    stricter = settings.model_copy(update={"score_threshold": 0.61})
    assert not signal_score(scored, stricter).passed


def test_signal_score_with_all_data_missing_is_zero(settings):
    result = signal_score(components(None, None, settings), settings)
    assert result.value == 0.0
    assert not result.passed
    assert all(c.reason.startswith("missing") for c in result.components)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_score.py -q`
Expected: FAIL with `ImportError: cannot import name 'intraday_momentum'`.

- [ ] **Step 3: Add the two components and the combined score**

Add `from statistics import pstdev` to the imports of `src/auto_invest/rubric/score.py`, then append:

```python
def first_half_hour(bars, settings) -> tuple[Bar, ...]:
    return bars_in_window(bars, OPEN, FIRST_HALF_HOUR_END, settings.timezone)


def _half_hour_return(bars) -> float | None:
    if not complete(bars, "open", "close"):
        return None
    return bars[-1].close / bars[0].open - 1


def intraday_momentum(candidate: Candidate | None, market: MarketData | None, settings) -> ComponentScore:
    name = "intraday_momentum"
    reason = first_missing("Candidate", candidate, "timestamp") or first_missing("MarketData", market)
    if reason:
        return ComponentScore(name, 0.0, reason)
    today = _half_hour_return(first_half_hour(market.today_bars, settings))
    if today is None:
        return ComponentScore(name, 0.0, "missing: MarketData.today_bars needs the first half hour")
    sessions = recent_sessions(market, candidate, settings)
    past = [_half_hour_return(first_half_hour(s, settings)) for s in sessions]
    if not sessions or any(r is None for r in past):
        return ComponentScore(
            name, 0.0, f"missing: MarketData.history_bars needs {settings.history_sessions} sessions"
        )
    sigma = pstdev(past)
    if sigma == 0:
        value = 1.0 if today > 0 else 0.0 if today < 0 else 0.5
    else:
        value = clip(0.5 + today / (2 * sigma))
    return ComponentScore(name, value, f"first half hour {today:+.3%} against typical {sigma:.3%}")


def _half_hour_range_and_volume(bars) -> tuple[float, float] | None:
    if not complete(bars, "open", "high", "low", "volume") or bars[0].open <= 0:
        return None
    price_range = (max(b.high for b in bars) - min(b.low for b in bars)) / bars[0].open
    return price_range, sum(b.volume for b in bars)


def volatility_and_volume_conditions(
    candidate: Candidate | None, market: MarketData | None, settings
) -> ComponentScore:
    name = "volatility_and_volume_conditions"
    reason = first_missing("Candidate", candidate, "timestamp") or first_missing("MarketData", market)
    if reason:
        return ComponentScore(name, 0.0, reason)
    today = _half_hour_range_and_volume(first_half_hour(market.today_bars, settings))
    if today is None:
        return ComponentScore(name, 0.0, "missing: MarketData.today_bars needs the first half hour")
    sessions = recent_sessions(market, candidate, settings)
    past = [_half_hour_range_and_volume(first_half_hour(s, settings)) for s in sessions]
    if not sessions or any(p is None for p in past):
        return ComponentScore(
            name, 0.0, f"missing: MarketData.history_bars needs {settings.history_sessions} sessions"
        )
    mean_range = sum(p[0] for p in past) / len(past)
    mean_volume = sum(p[1] for p in past) / len(past)
    if mean_range <= 0 or mean_volume <= 0:
        return ComponentScore(name, 0.0, "history has no range or no volume in the first half hour")
    range_part = clip(today[0] / mean_range / 2)
    volume_part = clip(today[1] / mean_volume / 2)
    return ComponentScore(
        name,
        (range_part + volume_part) / 2,
        f"range {today[0] / mean_range:.2f}x and volume {today[1] / mean_volume:.2f}x the average",
    )


@dataclass(frozen=True)
class SignalScore:
    components: tuple[ComponentScore, ...]
    value: float
    threshold: float
    passed: bool


def components(candidate, market, settings) -> tuple[ComponentScore, ...]:
    return (
        trend_direction(market, settings),
        intraday_momentum(candidate, market, settings),
        volatility_and_volume_conditions(candidate, market, settings),
        opening_range_breakout(candidate, market, settings),
        relative_volume(candidate, market, settings),
    )


def signal_score(scored: tuple[ComponentScore, ...], settings) -> SignalScore:
    value = sum(c.value for c in scored) / len(scored)
    threshold = settings.score_threshold
    return SignalScore(scored, value, threshold, value >= threshold)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_score.py -q`
Expected: 22 passed.

- [ ] **Step 5: Commit**

```bash
git add src/auto_invest/rubric/score.py tests/test_score.py
git commit -m "feat: intraday momentum, volatility and volume components, combined score"
```

---

### Task 11: Decision record and `decide`

**Files:**
- Create: `src/auto_invest/rubric/decision.py`
- Create: `tests/test_decision.py`

**Interfaces:**
- Consumes: `RUBRIC_VERSION`; records; `available_settled_cash` (Task 3); `position_size`, `Size` (Task 5); `run_checks`, `CheckResult` (Task 8); `components`, `signal_score`, `SignalScore` (Task 10); `local` (Task 6).
- Produces: `DecisionRecord(rubric_version, symbol, timestamp, checks, score, size, verdict, rejected_by)` with `to_dict()`; `decide(candidate, market, instrument, account, ledger, settings) -> DecisionRecord`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_decision.py`:

```python
import json
from datetime import timedelta

from auto_invest.rubric import RUBRIC_VERSION
from auto_invest.rubric.decision import decide
from auto_invest.rubric.records import (
    AccountState,
    Candidate,
    InstrumentStatus,
    MarketData,
    Quote,
    Sale,
    SettlementLedger,
)
from conftest import DAY, daily_bars, history_bars, minute_bars, ts


def good_inputs():
    candidate = Candidate("SPY", 100.5, 98.49, ts(10, 30))
    market = MarketData(
        Quote("SPY", 100.49, 100.51, ts(10, 30)),
        minute_bars(count=61, open=100.0, step=0.01, volume=40000.0),
        history_bars(open=100.0, step=0.002, volume=20000.0),
        daily_bars(start_price=74.2, step=0.1),
    )
    instrument = InstrumentStatus("SPY", True, False)
    account = AccountState(5000.0, (), 0, 0.0, 0.0, True, True, ts(10, 30), settled_cash=5000.0)
    ledger = SettlementLedger(5000.0, 0.0, ())
    return candidate, market, instrument, account, ledger


def test_a_good_candidate_is_accepted(settings):
    record = decide(*good_inputs(), settings)
    assert record.verdict == "accepted"
    assert record.rejected_by is None
    assert record.rubric_version == RUBRIC_VERSION
    assert record.symbol == "SPY"
    assert len(record.checks) == 8
    assert all(check.passed for check in record.checks)
    assert record.score.passed
    assert record.size.shares == 12


def test_rejected_by_names_the_first_failing_check(settings):
    candidate, market, instrument, account, ledger = good_inputs()
    halted = InstrumentStatus("SPY", True, True)
    record = decide(candidate, market, halted, account, ledger, settings)
    assert record.verdict == "rejected"
    assert record.rejected_by == "instrument_is_eligible"
    assert len(record.checks) == 8


def test_rejected_by_signal_score_when_checks_pass(settings):
    candidate, market, instrument, account, ledger = good_inputs()
    weak = MarketData(market.quote, market.today_bars, market.history_bars, daily_bars(start_price=126.0, step=-0.1))
    strict = settings.model_copy(update={"score_threshold": 0.99})
    record = decide(candidate, weak, instrument, account, ledger, strict)
    assert record.verdict == "rejected"
    assert record.rejected_by == "signal_score"


def test_unsettled_proceeds_cannot_be_spent_today(settings):
    candidate, market, instrument, account, ledger = good_inputs()
    poor = AccountState(5000.0, (), 0, 0.0, 0.0, True, True, ts(10, 30), settled_cash=None)
    unsettled = SettlementLedger(50.0, 0.0, (Sale(DAY, 4950.0),))
    record = decide(candidate, market, instrument, poor, unsettled, settings)
    assert record.verdict == "rejected"
    assert record.size.shares == 0
    assert record.rejected_by == "trade_beats_its_costs"
    tomorrow = Candidate("SPY", 100.5, 98.49, ts(10, 30, day=DAY + timedelta(days=1)))
    later_ledger = SettlementLedger(50.0, 0.0, (Sale(DAY, 4950.0),))
    settled = decide(tomorrow, market, instrument, poor, later_ledger, settings)
    assert settled.size.shares == 12


def test_all_inputs_missing_still_records_all_eight_checks(settings):
    record = decide(None, None, None, None, None, settings)
    assert record.verdict == "rejected"
    assert record.rejected_by == "data_is_sane"
    assert [c.name for c in record.checks][0] == "data_is_sane"
    assert all(not c.passed for c in record.checks)
    assert record.symbol is None
    assert record.timestamp is None


def test_record_round_trips_through_json(settings):
    record = decide(*good_inputs(), settings)
    as_dict = record.to_dict()
    text = json.dumps(as_dict)
    back = json.loads(text)
    assert back["verdict"] == "accepted"
    assert back["timestamp"] == ts(10, 30).isoformat()
    assert isinstance(back["checks"], list)
    assert back["checks"][0]["name"] == "data_is_sane"
    assert back["score"]["components"][0]["name"] == "trend_direction"
    assert back["size"]["shares"] == 12


def test_a_rejected_record_reads_in_plain_words(settings):
    candidate, market, instrument, account, ledger = good_inputs()
    losing = AccountState(5000.0, (), 0, -30.0, -25.0, True, True, ts(10, 30), settled_cash=5000.0)
    record = decide(candidate, market, instrument, losing, ledger, settings).to_dict()
    failed = [c for c in record["checks"] if not c["passed"]]
    assert failed == [
        {
            "name": "daily_loss_limit_not_hit",
            "passed": False,
            "reason": "today's P&L -55.00 against the halt at -50.00",
        }
    ]
    assert record["rejected_by"] == "daily_loss_limit_not_hit"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_decision.py -q`
Expected: FAIL with `ModuleNotFoundError: auto_invest.rubric.decision`.

- [ ] **Step 3: Write the decision module**

Create `src/auto_invest/rubric/decision.py`:

```python
from dataclasses import asdict, dataclass
from datetime import datetime

from . import RUBRIC_VERSION
from .bars import local
from .checks import CheckResult, run_checks
from .records import AccountState, Candidate, InstrumentStatus, MarketData, SettlementLedger
from .score import SignalScore, components, signal_score
from .settlement import available_settled_cash
from .sizing import Size, position_size


@dataclass(frozen=True)
class DecisionRecord:
    rubric_version: str
    symbol: str | None
    timestamp: datetime | None
    checks: tuple[CheckResult, ...]
    score: SignalScore | None
    size: Size | None
    verdict: str
    rejected_by: str | None

    def to_dict(self) -> dict:
        return {
            "rubric_version": self.rubric_version,
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "checks": [asdict(check) for check in self.checks],
            "score": None
            if self.score is None
            else {**asdict(self.score), "components": [asdict(c) for c in self.score.components]},
            "size": None if self.size is None else asdict(self.size),
            "verdict": self.verdict,
            "rejected_by": self.rejected_by,
        }


def decide(
    candidate: Candidate | None,
    market: MarketData | None,
    instrument: InstrumentStatus | None,
    account: AccountState | None,
    ledger: SettlementLedger | None,
    settings,
) -> DecisionRecord:
    usable_cash = None
    if candidate is not None and candidate.timestamp is not None:
        on_date = local(candidate.timestamp, settings.timezone).date()
        usable_cash = available_settled_cash(ledger, account, on_date)
    size = position_size(candidate, account, usable_cash, settings)
    checks = run_checks(candidate, market, instrument, account, usable_cash, size, settings)
    score = signal_score(components(candidate, market, settings), settings)
    failed = next((check.name for check in checks if not check.passed), None)
    if failed:
        rejected_by = failed
    elif not score.passed:
        rejected_by = "signal_score"
    elif size.shares < 1:
        rejected_by = "position_size"
    else:
        rejected_by = None
    return DecisionRecord(
        RUBRIC_VERSION,
        candidate.symbol if candidate else None,
        candidate.timestamp if candidate else None,
        checks,
        score,
        size,
        "rejected" if rejected_by else "accepted",
        rejected_by,
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_decision.py -q`
Expected: 7 passed. If `test_a_good_candidate_is_accepted` fails on the score, print `record.score` and adjust only the `good_inputs` market data (step sizes or volumes), never a formula; the spec's formulas are fixed.

- [ ] **Step 5: Commit**

```bash
git add src/auto_invest/rubric/decision.py tests/test_decision.py
git commit -m "feat: decision record and the decide pipeline"
```

---

### Task 12: Phase acceptance

**Files:**
- No new files. Verification only.

- [ ] **Step 1: Run the whole suite**

Run: `uv run pytest -q`
Expected: every test passes; the count is the sum of the task expectations plus the 19 pre-existing tests.

- [ ] **Step 2: Run the import guard on its own and read its assertions**

Run: `uv run pytest tests/test_rubric_imports.py -v`
Expected: both tests PASS. This is spec acceptance item 2.

- [ ] **Step 3: Print a rejected decision record and read it**

Run, from Git Bash:

```bash
PYTHONPATH=tests uv run python -c "
import json
from test_decision import good_inputs
from auto_invest.rubric.decision import decide
from auto_invest.rubric.records import InstrumentStatus
from auto_invest.settings import load_settings
c, m, i, a, l = good_inputs()
print(json.dumps(decide(c, m, InstrumentStatus('SPY', True, True), a, l, load_settings()).to_dict(), indent=2))
"
```

Expected: `"verdict": "rejected"`, `"rejected_by": "instrument_is_eligible"`, and the reason `"SPY is halted"`. This is spec acceptance item 5.

- [ ] **Step 4: Run the secret scanner over everything**

Run: `pre-commit run --all-files`
Expected: `Detect hardcoded secrets.....Passed`.

- [ ] **Step 5: Tick the Phase 1 checklist in the build plan and commit**

In `docs/build-plan.md`, change each `- [ ]` under "Phase 1: Rubric core → Checklist" to `- [x]`.

```bash
git add docs/build-plan.md
git commit -m "docs: tick the Phase 1 checklist"
```

---

## Spec coverage

| Spec | Task |
|---|---|
| R1.1 to R1.5 | 2 (import guard, records, version), 8 and 11 (timezone use) |
| B2, R2.1, R2.2 | 2 |
| R3.1 to R3.4 | 3 |
| R4.1 to R4.6 | 4 |
| R5.1 to R5.7 | 5 |
| B6 checks 1 to 3, R6.1 | 7 |
| B6 checks 4 to 8, R6.1, R6.2, R6.3 | 8 |
| B7 trend, breakout, relative volume, R7.2 | 9 |
| B7 momentum, volatility and volume, R7.1, R7.2 | 10 |
| R8.1 to R8.5 | 11 |
| B9, R9.1 | 1 |
| B11 acceptance | 12 |
