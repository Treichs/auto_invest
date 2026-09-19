# Phase 2 LEAN Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A thin LEAN adapter so the Phase 1 rubric can be backtested unchanged on QuantConnect's free plan, on SPY and QQQ at minute resolution, with Interactive Brokers Tiered costs, plus the script, docs, and runbook that make each run repeatable and byte-identical to the repo.

**Architecture:** `lean_adapter.py` is plain Python (no LEAN import) that converts LEAN data into rubric records, keeps the session bar store and the day ledger, proposes the candidate, serialises decisions, and hashes the rubric; every function is unit-tested locally. `main.py` is the `QCAlgorithm` glue: scheduling, orders, fee model, Object Store; it is exercised only by the cloud backtest. A build script writes the paste-ready project tree and prints the rubric hash; the algorithm logs the same hash at start.

**Tech Stack:** Python 3.12 locally (`uv`, pytest, pydantic); QuantConnect cloud (LEAN, Python 3.11, `pydantic` 2.12 available, `tomllib` not needed in the cloud). Standard library only inside `lean_adapter.py`.

**Spec:** `docs/superpowers/specs/2026-09-18-phase-2-lean-adapter-design.md`

## Global Constraints

- The rubric package `src/auto_invest/rubric/` is never edited (spec R1.12). `config/ceilings.toml` is never edited (B8).
- `lean_adapter.py` imports only the standard library and `rubric.*`; a test fails on `AlgorithmImports`, `QuantConnect`, `nautilus_trader`, `pandas`, `numpy` (R9.9).
- Both adapter files import the rubric as `rubric.…`, never `auto_invest.rubric` (R2.2).
- Every timestamp handed to the rubric is timezone-aware in America/New_York (R1.1).
- Hold-out starts 2025-01-01 (ADR 0017); `initialize` raises on any end date on or after it (R3.1).
- No loose comments in code. No file lists in documentation. Commit after every task with the message given; never push.
- Run every command from the repo root `C:\Dev\Git\auto_invest`. `uv run pytest` is the test command.

## File Structure

| Path | Responsibility |
|---|---|
| `config/settings.toml`, `src/auto_invest/settings.py`, `tests/test_settings.py` (modify) | `candidate_interval_minutes` |
| `pyproject.toml` (modify) | pytest `pythonpath` so `rubric`, `lean_adapter`, and the scripts import locally as they do in the cloud |
| `src/auto_invest/adapters/__init__.py`, `src/auto_invest/adapters/lean/__init__.py` | Empty package markers |
| `src/auto_invest/adapters/lean/lean_adapter.py` | Conversions, `SessionStore`, `DayLedger`, candidate, decision line, rejection counts, rubric hash |
| `src/auto_invest/adapters/lean/main.py` | `TieredFeeModel`, `RubricAlgorithm` |
| `scripts/build_quantconnect_project.py` | Writes `build/quantconnect/`, generates `settings_snapshot.py`, prints hash and commit |
| `scripts/count_rejections.py` | Counts `rejected_by` in a downloaded decisions file |
| `tests/test_lean_adapter.py`, `tests/test_build_quantconnect_project.py` | Tests for the above |
| `docs/research-log.md` | One row per run |
| `docs/runbooks/quantconnect-baseline-backtest.md` | Literal steps for pasting and running |
| `docs/build-plan.md` (modify) | Phase 2 checklist ticks |

---

### Task 1: Settings key and local import paths

**Files:**
- Modify: `config/settings.toml`
- Modify: `src/auto_invest/settings.py:51-56`
- Modify: `tests/test_settings.py:31-37` (the `EXTRA` dictionary)
- Modify: `pyproject.toml`
- Create: `src/auto_invest/adapters/__init__.py`, `src/auto_invest/adapters/lean/__init__.py` (both empty)

**Interfaces:**
- Produces: `Settings.candidate_interval_minutes: int`, read by `main.py` in Task 9. pytest can `import rubric`, `import lean_adapter`, and `import build_quantconnect_project`.

- [ ] **Step 1: Write the failing test**

Add `"candidate_interval_minutes": 5,` to `EXTRA` in `tests/test_settings.py` and append this test at the end of the file:

```python
def test_candidate_interval_is_a_positive_int_and_not_ceilinged():
    settings = load_settings()
    assert settings.candidate_interval_minutes == 5
    assert "candidate_interval_minutes" not in Ceilings.model_fields
    with pytest.raises(ValidationError):
        Settings.model_validate({**BASE, **EXTRA, "candidate_interval_minutes": 0})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_settings.py -q`
Expected: failures mentioning `candidate_interval_minutes` (extra field forbidden, and the new test).

- [ ] **Step 3: Add the setting**

In `config/settings.toml`, after `history_sessions = 20`, add:

```toml
candidate_interval_minutes = 5
```

In `src/auto_invest/settings.py`, inside `class Settings(Limits):` after `history_sessions: int = Field(gt=0)`, add:

```python
    candidate_interval_minutes: int = Field(gt=0)
```

- [ ] **Step 4: Add the pytest paths and package markers**

In `pyproject.toml`, replace the pytest section with:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src/auto_invest", "src/auto_invest/adapters/lean", "scripts"]
```

Create the two empty files `src/auto_invest/adapters/__init__.py` and `src/auto_invest/adapters/lean/__init__.py`, and an empty folder `scripts/` (git keeps it once Task 6 adds a file; for now create the folder only).

- [ ] **Step 5: Run the whole suite**

Run: `uv run pytest -q`
Expected: all pass, 150 tests.

- [ ] **Step 6: Commit**

```bash
git add config/settings.toml src/auto_invest/settings.py tests/test_settings.py pyproject.toml src/auto_invest/adapters/__init__.py src/auto_invest/adapters/lean/__init__.py
git commit -m "feat: candidate interval setting and local import paths for the LEAN adapter"
```

---

### Task 2: Conversions and instrument status

**Files:**
- Create: `src/auto_invest/adapters/lean/lean_adapter.py`
- Create: `tests/test_lean_adapter.py`

**Interfaces:**
- Produces: `TIMEZONE: str`, `aware(moment: datetime) -> datetime`, `to_bar(symbol: str, trade_bar) -> Bar`, `to_quote(symbol: str, quote_bar) -> Quote`, `instrument_status(symbol: str, trade_bar, listed_in_us: bool) -> InstrumentStatus`. `trade_bar` has LEAN's attributes `time, open, high, low, close, volume, is_fill_forward`; `quote_bar` has `bid, ask` (each with `.close`, or `None`) and `end_time`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_lean_adapter.py`:

```python
import ast
import pathlib
import sys
from dataclasses import dataclass
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import pytest

import lean_adapter
from lean_adapter import aware, instrument_status, to_bar, to_quote
from rubric.records import Bar, InstrumentStatus, Quote
from test_rubric_imports import FORBIDDEN, imported_names

ET = ZoneInfo("America/New_York")
DAY = date(2019, 3, 5)


@dataclass
class FakeTradeBar:
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    is_fill_forward: bool = False


@dataclass
class FakeSide:
    close: float


@dataclass
class FakeQuoteBar:
    bid: FakeSide | None
    ask: FakeSide | None
    end_time: datetime


def naive(hh: int, mm: int, day: date = DAY) -> datetime:
    return datetime.combine(day, time(hh, mm))


def fake_bar(hh: int, mm: int, day: date = DAY, low: float = 99.0, volume: float = 5000.0, fill_forward: bool = False) -> FakeTradeBar:
    return FakeTradeBar(naive(hh, mm, day), 100.0, 101.0, low, 100.5, volume, fill_forward)


def test_lean_adapter_imports_only_stdlib_and_rubric():
    path = pathlib.Path(lean_adapter.__file__)
    for name, level in imported_names(path):
        top = name.split(".")[0]
        assert top not in FORBIDDEN, f"imports {name}"
        assert level == 0
        assert top == "rubric" or top in sys.stdlib_module_names, f"imports {name}"


def test_aware_attaches_new_york_to_naive_and_converts_aware():
    assert aware(naive(10, 5)) == datetime(2019, 3, 5, 10, 5, tzinfo=ET)
    utc = datetime(2019, 3, 5, 15, 5, tzinfo=ZoneInfo("UTC"))
    assert aware(utc) == datetime(2019, 3, 5, 10, 5, tzinfo=ET)


def test_to_bar_maps_every_field_and_is_aware():
    bar = to_bar("SPY", fake_bar(9, 30))
    assert bar == Bar("SPY", datetime(2019, 3, 5, 9, 30, tzinfo=ET), 100.0, 101.0, 99.0, 100.5, 5000.0)


def test_to_quote_maps_bid_ask_close_and_end_time():
    quote = to_quote("SPY", FakeQuoteBar(FakeSide(99.99), FakeSide(100.01), naive(10, 5)))
    assert quote == Quote("SPY", 99.99, 100.01, datetime(2019, 3, 5, 10, 5, tzinfo=ET))


@pytest.mark.parametrize("quote_bar", [None, FakeQuoteBar(None, FakeSide(1.0), naive(10, 5)), FakeQuoteBar(FakeSide(1.0), None, naive(10, 5))])
def test_to_quote_missing_side_gives_none_fields(quote_bar):
    assert to_quote("SPY", quote_bar) == Quote("SPY", None, None, None)


def test_instrument_status_real_bar_is_not_halted():
    assert instrument_status("SPY", fake_bar(10, 5), True) == InstrumentStatus("SPY", True, False)


@pytest.mark.parametrize("bar", [None, fake_bar(10, 5, fill_forward=True)])
def test_instrument_status_missing_or_fill_forward_bar_is_halted(bar):
    assert instrument_status("SPY", bar, True) == InstrumentStatus("SPY", True, True)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_lean_adapter.py -q`
Expected: `ModuleNotFoundError: No module named 'lean_adapter'`.

- [ ] **Step 3: Write the module**

Create `src/auto_invest/adapters/lean/lean_adapter.py`:

```python
from datetime import datetime
from zoneinfo import ZoneInfo

from rubric.records import Bar, InstrumentStatus, Quote

TIMEZONE = "America/New_York"
NEW_YORK = ZoneInfo(TIMEZONE)


def aware(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=NEW_YORK)
    return moment.astimezone(NEW_YORK)


def to_bar(symbol: str, trade_bar) -> Bar:
    return Bar(
        symbol,
        aware(trade_bar.time),
        float(trade_bar.open),
        float(trade_bar.high),
        float(trade_bar.low),
        float(trade_bar.close),
        float(trade_bar.volume),
    )


def to_quote(symbol: str, quote_bar) -> Quote:
    if quote_bar is None or quote_bar.bid is None or quote_bar.ask is None:
        return Quote(symbol, None, None, None)
    return Quote(symbol, float(quote_bar.bid.close), float(quote_bar.ask.close), aware(quote_bar.end_time))


def instrument_status(symbol: str, trade_bar, listed_in_us: bool) -> InstrumentStatus:
    halted = trade_bar is None or bool(trade_bar.is_fill_forward)
    return InstrumentStatus(symbol, listed_in_us, halted)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_lean_adapter.py -q`
Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add src/auto_invest/adapters/lean/lean_adapter.py tests/test_lean_adapter.py
git commit -m "feat: LEAN bar, quote, and instrument status conversion"
```

---

### Task 3: Session store

**Files:**
- Modify: `src/auto_invest/adapters/lean/lean_adapter.py`
- Modify: `tests/test_lean_adapter.py`

**Interfaces:**
- Produces: `class SessionStore(history_sessions: int)` with `add(bar: Bar, fill_forward: bool) -> None`, `set_daily(bars: Iterable[Bar], today: date) -> None`, `today_bars() -> tuple[Bar, ...]`, `history_bars() -> tuple[Bar, ...]`, attribute `daily: tuple[Bar, ...]`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_lean_adapter.py`:

```python
from datetime import timedelta

from lean_adapter import SessionStore


def session_of(day: date, count: int = 3) -> list[Bar]:
    return [to_bar("SPY", fake_bar(9, 30 + i, day)) for i in range(count)]


def weekdays_before(day: date, count: int) -> list[date]:
    days = []
    cursor = day - timedelta(days=1)
    while len(days) < count:
        if cursor.weekday() < 5:
            days.append(cursor)
        cursor -= timedelta(days=1)
    return list(reversed(days))


def test_store_keeps_today_in_order_and_rolls_on_a_new_date():
    store = SessionStore(20)
    yesterday = weekdays_before(DAY, 1)[0]
    for bar in session_of(yesterday):
        store.add(bar, False)
    assert store.history_bars() == ()
    today = session_of(DAY)
    for bar in today:
        store.add(bar, False)
    assert store.today_bars() == tuple(today)
    assert store.history_bars() == tuple(session_of(yesterday))


def test_store_drops_the_oldest_session_beyond_the_cap():
    store = SessionStore(2)
    days = weekdays_before(DAY, 3)
    for day in days:
        for bar in session_of(day):
            store.add(bar, False)
    for bar in session_of(DAY):
        store.add(bar, False)
    history = store.history_bars()
    assert history[0].start.date() == days[1]
    assert history[-1].start.date() == days[2]
    assert len(history) == 6


def test_store_ignores_fill_forward_bars():
    store = SessionStore(20)
    store.add(to_bar("SPY", fake_bar(9, 30)), False)
    store.add(to_bar("SPY", fake_bar(9, 31, fill_forward=True)), True)
    assert len(store.today_bars()) == 1


def test_set_daily_drops_a_bar_dated_today():
    store = SessionStore(20)
    days = weekdays_before(DAY, 2)
    bars = [to_bar("SPY", fake_bar(9, 30, d)) for d in days] + [to_bar("SPY", fake_bar(9, 30, DAY))]
    store.set_daily(bars, DAY)
    assert [bar.start.date() for bar in store.daily] == days
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_lean_adapter.py -q`
Expected: `ImportError: cannot import name 'SessionStore'`.

- [ ] **Step 3: Add the store**

Append to `lean_adapter.py` (add `from datetime import date, datetime` at the top in place of the existing datetime import, and `from typing import Iterable`):

```python
class SessionStore:
    def __init__(self, history_sessions: int):
        self.history_sessions = history_sessions
        self.session_date: date | None = None
        self.today: list[Bar] = []
        self.sessions: dict[date, tuple[Bar, ...]] = {}
        self.daily: tuple[Bar, ...] = ()

    def add(self, bar: Bar, fill_forward: bool) -> None:
        if fill_forward:
            return
        day = bar.start.date()
        if day != self.session_date:
            self._roll(day)
        self.today.append(bar)

    def _roll(self, day: date) -> None:
        if self.session_date is not None and self.today:
            self.sessions[self.session_date] = tuple(self.today)
            while len(self.sessions) > self.history_sessions:
                del self.sessions[min(self.sessions)]
        self.session_date = day
        self.today = []

    def set_daily(self, bars: Iterable[Bar], today: date) -> None:
        self.daily = tuple(bar for bar in bars if bar.start.date() < today)

    def today_bars(self) -> tuple[Bar, ...]:
        return tuple(self.today)

    def history_bars(self) -> tuple[Bar, ...]:
        return tuple(bar for day in sorted(self.sessions) for bar in self.sessions[day])
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_lean_adapter.py -q`
Expected: 14 passed.

- [ ] **Step 5: Commit**

```bash
git add src/auto_invest/adapters/lean/lean_adapter.py tests/test_lean_adapter.py
git commit -m "feat: session store rolling minute bars into history"
```

---

### Task 4: Day ledger, account state, settlement ledger

**Files:**
- Modify: `src/auto_invest/adapters/lean/lean_adapter.py`
- Modify: `tests/test_lean_adapter.py`

**Interfaces:**
- Produces: `class DayLedger` with `begin_session(equity: float, settled_cash: float, net_profit: float)`, `record_buy(value: float, fee: float)`, `record_sell(day: date, value: float, fee: float)`, `settlement_ledger() -> SettlementLedger`, `account_state(positions: Iterable[Position], settled_cash: float, net_profit: float, unrealised: float, now: datetime) -> AccountState`; attributes `entries_today`, `buys_today`, `sales`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_lean_adapter.py`:

```python
from lean_adapter import DayLedger
from rubric.records import AccountState, Position, Sale, SettlementLedger


def started_ledger() -> DayLedger:
    ledger = DayLedger()
    ledger.begin_session(5000.0, 4800.0, 120.0)
    return ledger


def test_ledger_counts_fills_and_adds_fees_to_buys():
    ledger = started_ledger()
    ledger.record_buy(1250.0, 0.35)
    ledger.record_buy(600.0, 0.35)
    assert ledger.entries_today == 2
    assert ledger.buys_today == pytest.approx(1850.70)


def test_ledger_sales_are_todays_only_and_net_of_fees():
    ledger = started_ledger()
    ledger.record_sell(DAY, 1260.0, 0.35)
    assert ledger.sales == (Sale(DAY, 1259.65),)
    assert ledger.settlement_ledger() == SettlementLedger(4800.0, 0.0, (Sale(DAY, 1259.65),))


def test_ledger_resets_at_session_start():
    ledger = started_ledger()
    ledger.record_buy(1250.0, 0.35)
    ledger.record_sell(DAY, 1260.0, 0.35)
    ledger.begin_session(5010.0, 5010.0, 130.0)
    assert (ledger.entries_today, ledger.buys_today, ledger.sales) == (0, 0.0, ())
    assert ledger.settlement_ledger() == SettlementLedger(5010.0, 0.0, ())


def test_account_state_realised_is_net_profit_since_session_start():
    ledger = started_ledger()
    ledger.record_buy(1250.0, 0.35)
    positions = [Position("SPY", 5.0, 250.0, 248.0)]
    state = ledger.account_state(positions, 3550.0, 125.5, -3.0, naive(10, 5))
    assert state == AccountState(
        5000.0, (Position("SPY", 5.0, 250.0, 248.0),), 1, 5.5, -3.0, True, True,
        datetime(2019, 3, 5, 10, 5, tzinfo=ET), 3550.0,
    )


def test_account_state_before_any_session_has_none_equity_and_realised():
    state = DayLedger().account_state([], 5000.0, 0.0, 0.0, naive(10, 5))
    assert state.start_of_day_equity is None
    assert state.realised_pnl_today is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_lean_adapter.py -q`
Expected: `ImportError: cannot import name 'DayLedger'`.

- [ ] **Step 3: Add the ledger**

Append to `lean_adapter.py` (extend the records import to `AccountState, Bar, InstrumentStatus, Position, Quote, Sale, SettlementLedger`):

```python
class DayLedger:
    def __init__(self):
        self.start_equity: float | None = None
        self.start_settled_cash: float | None = None
        self.start_net_profit: float | None = None
        self.entries_today = 0
        self.buys_today = 0.0
        self.sales: tuple[Sale, ...] = ()

    def begin_session(self, equity: float, settled_cash: float, net_profit: float) -> None:
        self.start_equity = equity
        self.start_settled_cash = settled_cash
        self.start_net_profit = net_profit
        self.entries_today = 0
        self.buys_today = 0.0
        self.sales = ()

    def record_buy(self, value: float, fee: float) -> None:
        self.entries_today += 1
        self.buys_today += value + fee

    def record_sell(self, day: date, value: float, fee: float) -> None:
        self.sales += (Sale(day, value - fee),)

    def settlement_ledger(self) -> SettlementLedger:
        return SettlementLedger(self.start_settled_cash, self.buys_today, self.sales)

    def account_state(
        self,
        positions: Iterable[Position],
        settled_cash: float,
        net_profit: float,
        unrealised: float,
        now: datetime,
    ) -> AccountState:
        realised = None if self.start_net_profit is None else net_profit - self.start_net_profit
        return AccountState(
            self.start_equity,
            tuple(positions),
            self.entries_today,
            realised,
            unrealised,
            True,
            True,
            aware(now),
            settled_cash,
        )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_lean_adapter.py -q`
Expected: 19 passed.

- [ ] **Step 5: Commit**

```bash
git add src/auto_invest/adapters/lean/lean_adapter.py tests/test_lean_adapter.py
git commit -m "feat: day ledger building account state and settlement ledger"
```

---

### Task 5: Candidate, opening-range stop, market data

**Files:**
- Modify: `src/auto_invest/adapters/lean/lean_adapter.py`
- Modify: `tests/test_lean_adapter.py`

**Interfaces:**
- Produces: `opening_range_low(today_bars: Iterable[Bar], minutes: int) -> float | None`, `candidate(symbol: str, quote: Quote, today_bars: Iterable[Bar], minutes: int, now: datetime) -> Candidate`, `market_data(quote: Quote, store: SessionStore) -> MarketData`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_lean_adapter.py`:

```python
from lean_adapter import candidate, market_data, opening_range_low
from rubric.records import Candidate, MarketData


def opening_bars(lows=(99.5, 99.2, 99.8, 99.4, 99.9)) -> list[Bar]:
    return [to_bar("SPY", fake_bar(9, 30 + i, low=low)) for i, low in enumerate(lows)]


def test_opening_range_low_is_the_lowest_low_of_the_first_minutes():
    bars = opening_bars() + [to_bar("SPY", fake_bar(9, 35, low=90.0))]
    assert opening_range_low(bars, 5) == 99.2


def test_opening_range_low_is_none_when_a_bar_is_missing():
    assert opening_range_low(opening_bars()[:4], 5) is None
    assert opening_range_low((), 5) is None


def test_candidate_uses_the_ask_and_the_range_low_and_is_aware():
    quote = Quote("SPY", 99.99, 100.01, aware(naive(10, 5)))
    result = candidate("SPY", quote, opening_bars(), 5, naive(10, 5))
    assert result == Candidate("SPY", 100.01, 99.2, datetime(2019, 3, 5, 10, 5, tzinfo=ET))


def test_candidate_with_no_quote_or_range_carries_none_for_the_rubric_to_reject():
    result = candidate("SPY", Quote("SPY", None, None, None), (), 5, naive(10, 5))
    assert (result.entry_price, result.stop_price) == (None, None)


def test_market_data_bundles_the_store():
    store = SessionStore(20)
    for bar in opening_bars():
        store.add(bar, False)
    quote = Quote("SPY", 99.99, 100.01, aware(naive(10, 5)))
    assert market_data(quote, store) == MarketData(quote, tuple(opening_bars()), (), ())
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_lean_adapter.py -q`
Expected: `ImportError: cannot import name 'candidate'`.

- [ ] **Step 3: Add the functions**

Append to `lean_adapter.py` (add `from datetime import date, datetime, timedelta`, `from rubric.bars import bars_in_window`, `from rubric.score import OPEN`, and extend the records import with `Candidate, MarketData`):

```python
def opening_range_low(today_bars: Iterable[Bar], minutes: int) -> float | None:
    end = (datetime.combine(datetime.min, OPEN) + timedelta(minutes=minutes)).time()
    window = bars_in_window(today_bars, OPEN, end, TIMEZONE)
    if len(window) != minutes:
        return None
    return min(bar.low for bar in window)


def candidate(symbol: str, quote: Quote, today_bars: Iterable[Bar], minutes: int, now: datetime) -> Candidate:
    return Candidate(symbol, quote.ask, opening_range_low(today_bars, minutes), aware(now))


def market_data(quote: Quote, store: SessionStore) -> MarketData:
    return MarketData(quote, store.today_bars(), store.history_bars(), store.daily)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_lean_adapter.py -q`
Expected: 24 passed.

- [ ] **Step 5: Commit**

```bash
git add src/auto_invest/adapters/lean/lean_adapter.py tests/test_lean_adapter.py
git commit -m "feat: candidate at the ask with the opening-range low as the stop"
```

---

### Task 6: Decision line, rejection counts, count script

**Files:**
- Modify: `src/auto_invest/adapters/lean/lean_adapter.py`
- Modify: `tests/test_lean_adapter.py`
- Create: `scripts/count_rejections.py`

**Interfaces:**
- Produces: `decision_line(record: DecisionRecord) -> str` (one JSON object, no newline), `rejection_counts(lines: Iterable[str]) -> dict[str, int]` (key `"accepted"` for accepted lines).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_lean_adapter.py`:

```python
import json

from lean_adapter import decision_line, rejection_counts
from rubric.checks import CheckResult
from rubric.decision import DecisionRecord
from rubric.score import ComponentScore, SignalScore
from rubric.sizing import Size

CHECKS = tuple(CheckResult(name, True, "ok") for name in (
    "data_is_sane", "instrument_is_eligible", "market_is_liquid", "trade_beats_its_costs",
    "exit_is_defined", "risk_budget_has_room", "daily_loss_limit_not_hit", "system_is_healthy",
))
SCORE = SignalScore((ComponentScore("trend_direction", 1.0, "4 of 4"),), 0.8, 0.6, True)


def record(verdict: str, rejected_by: str | None, checks=CHECKS, score=SCORE, size=Size(1250.0, 5, 25.0, 25.0)):
    return DecisionRecord("0.1.0", "SPY", aware(naive(10, 5)), checks, score, size, verdict, rejected_by)


def test_decision_line_for_a_rejected_check_names_it_and_its_reason():
    checks = CHECKS[:2] + (CheckResult("market_is_liquid", False, "spread 0.0600% is over the cap 0.0500%"),) + CHECKS[3:]
    line = json.loads(decision_line(record("rejected", "market_is_liquid", checks)))
    assert line["rejected_by"] == "market_is_liquid"
    assert line["reason"] == "spread 0.0600% is over the cap 0.0500%"
    assert line["checks"]["market_is_liquid"] is False and line["checks"]["data_is_sane"] is True
    assert (line["score"], line["shares"], line["symbol"], line["rubric_version"]) == (0.8, 5, "SPY", "0.1.0")
    assert line["timestamp"] == "2019-03-05T10:05:00-05:00"
    assert "record" not in line


def test_decision_line_for_a_score_rejection_states_the_threshold():
    score = SignalScore(SCORE.components, 0.4, 0.6, False)
    line = json.loads(decision_line(record("rejected", "signal_score", score=score)))
    assert line["reason"] == "score 0.400 is under the threshold 0.6"


def test_decision_line_for_an_accepted_decision_carries_the_full_record():
    full = record("accepted", None)
    line = json.loads(decision_line(full))
    assert line["reason"] is None
    assert line["record"] == full.to_dict()


def test_rejection_counts_groups_by_rejected_by_with_accepted_as_a_key():
    lines = [
        decision_line(record("rejected", "market_is_liquid")),
        decision_line(record("rejected", "market_is_liquid")),
        decision_line(record("rejected", "signal_score")),
        decision_line(record("accepted", None)),
    ]
    assert rejection_counts(lines) == {"accepted": 1, "market_is_liquid": 2, "signal_score": 1}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_lean_adapter.py -q`
Expected: `ImportError: cannot import name 'decision_line'`.

- [ ] **Step 3: Add the functions**

Append to `lean_adapter.py` (add `import json` at the top):

```python
def decision_line(record) -> str:
    data = record.to_dict()
    failing = next((check for check in data["checks"] if not check["passed"]), None)
    score = data["score"]
    size = data["size"]
    if failing is not None:
        reason = failing["reason"]
    elif score is not None and not score["passed"]:
        reason = f"score {score['value']:.3f} is under the threshold {score['threshold']}"
    elif size is not None and size["shares"] < 1:
        reason = size["reason"] or "no shares to trade"
    else:
        reason = None
    line = {
        "timestamp": data["timestamp"],
        "symbol": data["symbol"],
        "verdict": data["verdict"],
        "rejected_by": data["rejected_by"],
        "reason": reason,
        "checks": {check["name"]: check["passed"] for check in data["checks"]},
        "score": None if score is None else score["value"],
        "shares": None if size is None else size["shares"],
        "rubric_version": data["rubric_version"],
    }
    if data["verdict"] == "accepted":
        line["record"] = data
    return json.dumps(line)


def rejection_counts(lines: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for line in lines:
        key = json.loads(line)["rejected_by"] or "accepted"
        counts[key] = counts.get(key, 0) + 1
    return counts
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_lean_adapter.py -q`
Expected: 28 passed.

- [ ] **Step 5: Add the count script**

Create `scripts/count_rejections.py`:

```python
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src" / "auto_invest"), str(ROOT / "src" / "auto_invest" / "adapters" / "lean")]

from lean_adapter import rejection_counts


def main(path: str) -> None:
    lines = [line for line in Path(path).read_text().splitlines() if line.strip()]
    counts = rejection_counts(lines)
    for key in sorted(counts, key=counts.get, reverse=True):
        print(f"{counts[key]:>7}  {key}")
    print(f"{len(lines):>7}  total")


if __name__ == "__main__":
    main(sys.argv[1])
```

Check it runs: write two lines from the test above to a temp file and run `uv run python scripts/count_rejections.py <file>`; expected output lists counts and a total.

- [ ] **Step 6: Commit**

```bash
git add src/auto_invest/adapters/lean/lean_adapter.py tests/test_lean_adapter.py scripts/count_rejections.py
git commit -m "feat: compact decision log line and rejection counts"
```

---

### Task 7: Rubric hash

**Files:**
- Modify: `src/auto_invest/adapters/lean/lean_adapter.py`
- Modify: `tests/test_lean_adapter.py`

**Interfaces:**
- Produces: `rubric_hash(folder: Path | str) -> str`, a 64-character hex SHA-256.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_lean_adapter.py`:

```python
import shutil

import auto_invest.rubric
from lean_adapter import rubric_hash

RUBRIC_DIR = pathlib.Path(auto_invest.rubric.__file__).parent


def test_rubric_hash_is_stable_and_hex():
    first = rubric_hash(RUBRIC_DIR)
    assert first == rubric_hash(str(RUBRIC_DIR))
    assert len(first) == 64 and int(first, 16) >= 0


def test_rubric_hash_changes_on_one_byte_and_ignores_line_endings(tmp_path):
    copy = tmp_path / "rubric"
    shutil.copytree(RUBRIC_DIR, copy, ignore=shutil.ignore_patterns("__pycache__"))
    assert rubric_hash(copy) == rubric_hash(RUBRIC_DIR)
    target = copy / "costs.py"
    target.write_bytes(target.read_bytes().replace(b"\n", b"\r\n"))
    assert rubric_hash(copy) == rubric_hash(RUBRIC_DIR)
    target.write_bytes(target.read_bytes() + b"#")
    assert rubric_hash(copy) != rubric_hash(RUBRIC_DIR)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_lean_adapter.py -q`
Expected: `ImportError: cannot import name 'rubric_hash'`.

- [ ] **Step 3: Add the function**

Append to `lean_adapter.py` (add `import hashlib` and `from pathlib import Path`):

```python
def rubric_hash(folder) -> str:
    digest = hashlib.sha256()
    for path in sorted(Path(folder).glob("*.py")):
        digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
    return digest.hexdigest()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest -q`
Expected: all pass, 180 tests.

- [ ] **Step 5: Commit**

```bash
git add src/auto_invest/adapters/lean/lean_adapter.py tests/test_lean_adapter.py
git commit -m "feat: rubric folder hash for the byte-identical check"
```

---

### Task 8: Build script and settings snapshot

**Files:**
- Create: `scripts/build_quantconnect_project.py`
- Create: `tests/test_build_quantconnect_project.py`
- Create: `src/auto_invest/adapters/lean/main.py` as a one-line placeholder so the build has a file to copy (Task 9 replaces it)

**Interfaces:**
- Produces: `build(out: Path) -> list[Path]` (the files written, sorted) and `snapshot_source() -> str`. Running the script writes `build/quantconnect/` and prints `wrote N files to …`, `rubric sha256 …`, `git commit …`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_build_quantconnect_project.py`:

```python
import pathlib
import runpy
import tomllib

from build_quantconnect_project import RUBRIC, ROOT, build, snapshot_source
from lean_adapter import rubric_hash
from settings import Ceilings, Settings, check_against_ceilings

EXPECTED = {
    "main.py", "lean_adapter.py", "settings.py", "settings_snapshot.py",
    *(f"rubric/{p.name}" for p in RUBRIC.glob("*.py")),
}


def test_build_writes_exactly_the_paste_ready_tree(tmp_path):
    out = tmp_path / "quantconnect"
    files = build(out)
    assert {p.relative_to(out).as_posix() for p in files} == EXPECTED
    assert len(files) == 13
    assert all(p.stat().st_size < 32 * 1024 for p in files)


def test_build_copies_the_rubric_byte_for_byte(tmp_path):
    out = tmp_path / "quantconnect"
    build(out)
    assert rubric_hash(out / "rubric") == rubric_hash(RUBRIC)
    for path in RUBRIC.glob("*.py"):
        assert (out / "rubric" / path.name).read_bytes() == path.read_bytes()
    assert (out / "settings.py").read_bytes() == (ROOT / "src" / "auto_invest" / "settings.py").read_bytes()


def test_snapshot_matches_the_toml_files_and_passes_the_ceiling_check(tmp_path):
    path = tmp_path / "settings_snapshot.py"
    path.write_text(snapshot_source())
    namespace = runpy.run_path(str(path))
    assert namespace["SETTINGS"] == tomllib.loads((ROOT / "config" / "settings.toml").read_text())
    assert namespace["CEILINGS"] == tomllib.loads((ROOT / "config" / "ceilings.toml").read_text())
    settings = Settings.model_validate(namespace["SETTINGS"])
    check_against_ceilings(settings, Ceilings.model_validate(namespace["CEILINGS"]))
    assert settings.candidate_interval_minutes == 5


def test_build_replaces_a_stale_tree(tmp_path):
    out = tmp_path / "quantconnect"
    out.mkdir()
    (out / "stale.py").write_text("x = 1\n")
    build(out)
    assert not (out / "stale.py").exists()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_build_quantconnect_project.py -q`
Expected: `ModuleNotFoundError: No module named 'build_quantconnect_project'`.

- [ ] **Step 3: Write the placeholder and the script**

Create `src/auto_invest/adapters/lean/main.py` containing only:

```python
from AlgorithmImports import *
```

Create `scripts/build_quantconnect_project.py`:

```python
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "auto_invest"
ADAPTER = PACKAGE / "adapters" / "lean"
RUBRIC = PACKAGE / "rubric"
CONFIG = ROOT / "config"
OUT = ROOT / "build" / "quantconnect"

sys.path[:0] = [str(PACKAGE), str(ADAPTER)]

from lean_adapter import rubric_hash


def snapshot_source() -> str:
    settings = tomllib.loads((CONFIG / "settings.toml").read_text())
    ceilings = tomllib.loads((CONFIG / "ceilings.toml").read_text())
    return f"SETTINGS = {settings!r}\nCEILINGS = {ceilings!r}\n"


def build(out: Path = OUT) -> list[Path]:
    if out.exists():
        shutil.rmtree(out)
    (out / "rubric").mkdir(parents=True)
    for name in ("main.py", "lean_adapter.py"):
        shutil.copyfile(ADAPTER / name, out / name)
    shutil.copyfile(PACKAGE / "settings.py", out / "settings.py")
    (out / "settings_snapshot.py").write_text(snapshot_source(), newline="\n")
    for path in sorted(RUBRIC.glob("*.py")):
        shutil.copyfile(path, out / "rubric" / path.name)
    return sorted(path for path in out.rglob("*") if path.is_file())


def main() -> None:
    files = build()
    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT
    ).stdout.strip()
    print(f"wrote {len(files)} files to {OUT}")
    print(f"rubric sha256 {rubric_hash(RUBRIC)}")
    print(f"git commit {commit}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the tests and the script**

Run: `uv run pytest tests/test_build_quantconnect_project.py -q`
Expected: 4 passed.

Run: `uv run python scripts/build_quantconnect_project.py`
Expected: three lines: `wrote 13 files to C:\Dev\Git\auto_invest\build\quantconnect`, `rubric sha256 <64 hex>`, `git commit <7 hex>`. `git status --short` shows nothing under `build/` (it is git-ignored).

- [ ] **Step 5: Commit**

```bash
git add scripts/build_quantconnect_project.py tests/test_build_quantconnect_project.py src/auto_invest/adapters/lean/main.py
git commit -m "feat: build script writing the paste-ready QuantConnect tree"
```

---

### Task 9: The LEAN algorithm

**Files:**
- Replace: `src/auto_invest/adapters/lean/main.py`

**Interfaces:**
- Consumes: everything `lean_adapter.py` exports (Tasks 2 to 7), `rubric.decision.decide`, `rubric.costs.commission_per_side`, `settings.Settings/Ceilings/check_against_ceilings`, and `settings_snapshot.SETTINGS/CEILINGS` (generated by Task 8, present only in the built tree).
- Not unit-tested locally (spec R9.10). Step 3 is a syntax check; Task 11 is the real check.

- [ ] **Step 1: Write the algorithm**

Replace `src/auto_invest/adapters/lean/main.py` with:

```python
from AlgorithmImports import *

import json
from datetime import date, timedelta
from pathlib import Path

import rubric
from lean_adapter import (
    DayLedger,
    SessionStore,
    candidate,
    decision_line,
    instrument_status,
    market_data,
    rejection_counts,
    rubric_hash,
    to_bar,
    to_quote,
)
from rubric import RUBRIC_VERSION
from rubric.costs import commission_per_side
from rubric.decision import decide
from rubric.records import Position
from settings import Ceilings, Settings, check_against_ceilings
from settings_snapshot import CEILINGS, SETTINGS

IN_SAMPLE_YEAR = 2019
HOLD_OUT_START = date(2025, 1, 1)
STARTING_CASH = 5000
WARM_UP = timedelta(days=35)
DAILY_BARS = 253
DONE = (OrderStatus.FILLED, OrderStatus.CANCELED, OrderStatus.INVALID)


class TieredFeeModel(FeeModel):
    def get_order_fee(self, parameters):
        shares = int(parameters.order.absolute_quantity)
        price = float(parameters.security.price)
        return OrderFee(CashAmount(commission_per_side(shares, price), "USD"))


class RubricAlgorithm(QCAlgorithm):
    def initialize(self):
        if date(IN_SAMPLE_YEAR, 12, 31) >= HOLD_OUT_START:
            raise ValueError(f"{IN_SAMPLE_YEAR} is inside the hold-out that starts {HOLD_OUT_START}, see ADR 0017")
        self.set_start_date(IN_SAMPLE_YEAR, 1, 1)
        self.set_end_date(IN_SAMPLE_YEAR, 12, 31)
        self.set_cash(STARTING_CASH)
        self.set_brokerage_model(BrokerageName.INTERACTIVE_BROKERS_BROKERAGE, AccountType.CASH)
        settings = Settings.model_validate(SETTINGS)
        check_against_ceilings(settings, Ceilings.model_validate(CEILINGS))
        self.rubric_settings = settings
        self.symbols = {}
        for ticker in settings.approved_symbols:
            security = self.add_equity(ticker, Resolution.MINUTE)
            security.set_fee_model(TieredFeeModel())
            self.symbols[ticker] = security.symbol
        self.stores = {ticker: SessionStore(settings.history_sessions) for ticker in self.symbols}
        self.ledger = DayLedger()
        self.session_date = None
        self.window_open = False
        self.closing = False
        self.entry_tickets = {}
        self.stop_tickets = {}
        self.stop_prices = {}
        self.close_tickets = {}
        self.candidates = {}
        self.lines = []
        self.set_warm_up(WARM_UP, Resolution.MINUTE)
        every_day = self.date_rules.every_day(next(iter(self.symbols.values())))
        self.schedule.on(every_day, self.at(settings.entry_window_start), self.open_window)
        self.schedule.on(every_day, self.at(settings.entry_window_end), self.close_window)
        self.schedule.on(every_day, self.at(settings.forced_close), self.forced_close)
        self.log(f"rubric {RUBRIC_VERSION} sha256 {rubric_hash(Path(rubric.__file__).parent)}")
        self.log(f"object store max size {self.object_store.max_size} bytes")

    def at(self, moment):
        return self.time_rules.at(moment.hour, moment.minute)

    def on_data(self, slice):
        today = self.time.date()
        if today != self.session_date:
            self.begin_session(today)
        for ticker, symbol in self.symbols.items():
            if symbol in slice.bars:
                bar = slice.bars[symbol]
                self.stores[ticker].add(to_bar(ticker, bar), bar.is_fill_forward)
        if self.is_warming_up:
            return
        if self.closing:
            self.reprice_closes()
            return
        if not self.window_open or self.time.minute % self.rubric_settings.candidate_interval_minutes:
            return
        for ticker, symbol in self.symbols.items():
            self.cancel_entry(ticker, "unfilled at the next candidate tick")
            if self.portfolio[symbol].invested:
                continue
            self.consider(ticker, symbol, slice)

    def begin_session(self, today):
        self.session_date = today
        self.window_open = False
        self.closing = False
        self.close_tickets = {}
        self.ledger.begin_session(
            float(self.portfolio.total_portfolio_value),
            float(self.portfolio.cash),
            float(self.portfolio.total_net_profit),
        )
        if self.is_warming_up:
            return
        for ticker, symbol in self.symbols.items():
            daily = self.history[TradeBar](symbol, DAILY_BARS, Resolution.DAILY)
            self.stores[ticker].set_daily([to_bar(ticker, bar) for bar in daily], today)

    def consider(self, ticker, symbol, slice):
        settings = self.rubric_settings
        store = self.stores[ticker]
        quote = to_quote(ticker, slice.quote_bars[symbol] if symbol in slice.quote_bars else None)
        bar = slice.bars[symbol] if symbol in slice.bars else None
        instrument = instrument_status(ticker, bar, symbol.id.market == Market.USA)
        positions = [
            Position(t, float(self.portfolio[s].quantity), float(self.portfolio[s].average_price), self.stop_prices.get(t))
            for t, s in self.symbols.items()
            if self.portfolio[s].invested
        ]
        account = self.ledger.account_state(
            positions,
            float(self.portfolio.cash),
            float(self.portfolio.total_net_profit),
            float(self.portfolio.total_unrealized_profit),
            self.time,
        )
        proposed = candidate(ticker, quote, store.today_bars(), settings.opening_range_minutes, self.time)
        record = decide(proposed, market_data(quote, store), instrument, account, self.ledger.settlement_ledger(), settings)
        self.lines.append(decision_line(record))
        if record.verdict != "accepted":
            return
        ticket = self.limit_order(symbol, record.size.shares, proposed.entry_price, tag=f"entry rubric {RUBRIC_VERSION}")
        self.entry_tickets[ticker] = ticket
        self.candidates[ticket.order_id] = proposed

    def cancel_entry(self, ticker, why):
        ticket = self.entry_tickets.pop(ticker, None)
        if ticket is not None and ticket.status not in DONE:
            ticket.cancel(why)

    def on_order_event(self, event):
        if event.status != OrderStatus.FILLED:
            return
        ticker = event.symbol.value
        quantity = abs(float(event.fill_quantity))
        value = float(event.fill_price) * quantity
        fee = float(event.order_fee.value.amount)
        proposed = self.candidates.pop(event.order_id, None)
        if proposed is not None:
            self.entry_tickets.pop(ticker, None)
            self.ledger.record_buy(value, fee)
            self.stop_tickets[ticker] = self.stop_market_order(event.symbol, -int(quantity), proposed.stop_price, tag="protective stop")
            self.stop_prices[ticker] = proposed.stop_price
            return
        self.ledger.record_sell(self.time.date(), value, fee)
        self.stop_tickets.pop(ticker, None)
        self.stop_prices.pop(ticker, None)
        self.close_tickets.pop(ticker, None)

    def open_window(self):
        if not self.is_warming_up:
            self.window_open = True

    def close_window(self):
        self.window_open = False
        for ticker in list(self.entry_tickets):
            self.cancel_entry(ticker, "entry window closed")

    def forced_close(self):
        if self.is_warming_up:
            return
        self.window_open = False
        self.closing = True
        for ticker in list(self.entry_tickets):
            self.cancel_entry(ticker, "forced close")
        for ticket in self.stop_tickets.values():
            if ticket.status not in DONE:
                ticket.cancel("forced close")
        self.stop_tickets = {}
        self.stop_prices = {}
        for ticker, symbol in self.symbols.items():
            holding = self.portfolio[symbol]
            if holding.invested:
                bid = float(self.securities[symbol].bid_price) or float(self.securities[symbol].price)
                self.close_tickets[ticker] = self.limit_order(symbol, -int(holding.quantity), bid, tag="forced close at the bid")

    def reprice_closes(self):
        for ticker, ticket in list(self.close_tickets.items()):
            if ticket.status in DONE:
                self.close_tickets.pop(ticker)
                continue
            ticket.update_limit_price(float(self.securities[self.symbols[ticker]].bid_price), "re-priced to the bid")

    def on_end_of_algorithm(self):
        key = f"auto_invest/{self.algorithm_id}/decisions.jsonl"
        self.object_store.save(key, "\n".join(self.lines) + "\n")
        self.log(f"decisions {len(self.lines)} saved to object store key {key}")
        self.log(f"rejections {json.dumps(rejection_counts(self.lines), sort_keys=True)}")
        self.log(f"orders {len(list(self.transactions.get_orders()))}")
```

- [ ] **Step 2: Rebuild the tree and run the suite**

Run: `uv run python scripts/build_quantconnect_project.py`
Expected: `wrote 13 files …`; the built `main.py` is byte-identical to the source (the build test covers this).

Run: `uv run pytest -q`
Expected: all pass, 184 tests.

- [ ] **Step 3: Syntax-check the algorithm locally**

Run: `uv run python -c "import ast, pathlib; ast.parse(pathlib.Path('src/auto_invest/adapters/lean/main.py').read_text()); print('main.py parses')"`
Expected: `main.py parses`. (It cannot be imported locally; `AlgorithmImports` exists only in the cloud.)

- [ ] **Step 4: Commit**

```bash
git add src/auto_invest/adapters/lean/main.py
git commit -m "feat: LEAN algorithm feeding the rubric and acting on its verdicts"
```

---

### Task 10: Research log, runbook, build-plan ticks

**Files:**
- Create: `docs/research-log.md`
- Create: `docs/runbooks/quantconnect-baseline-backtest.md`
- Modify: `docs/build-plan.md:177-186` (Phase 2 checklist)

- [ ] **Step 1: Write the research log**

Create `docs/research-log.md`:

```markdown
# Research log

One row per backtest run, appended before the result is looked at. Phase 3 counts the rows; the count sets the bar for the Deflated Sharpe Ratio, so never delete a row. Hold-out is 2025-01-01 onward ([ADR 0017](adr/0017-hold-out-period-from-2025.md)); a run with an end date in the hold-out does not belong here and must not be made.

Columns: the rubric hash is the first eight characters the backtest logs at start; trades, net return, and max drawdown come from the backtest Overview; the top check is the largest count in the `rejections` log line.

| Date | Year | What changed | Rubric hash | Trades | Net return after costs | Max drawdown | Top rejecting check (count) |
|---|---|---|---|---|---|---|---|
| | | | | | | | |
```

- [ ] **Step 2: Write the runbook**

Create `docs/runbooks/quantconnect-baseline-backtest.md`:

```markdown
# Runbook: baseline backtest on QuantConnect

The first runbook in this repo and the template for the rest: numbered steps, one action each, the exact label to click or value to type, one line on why, and what success looks like. Anything hard to undo is flagged before the step.

Time: about 40 minutes the first time, about 10 minutes for later runs. Cost: $0.

## Before you start

- The hold-out is 2025-01-01 onward. `IN_SAMPLE_YEAR` must be 2019 to 2024. The algorithm refuses anything later.
- You are pasting from `build/quantconnect/`, never from `src/`. The tree is rebuilt every time, so it always matches Git.

## A. Build the tree

1. Open a terminal in `C:\Dev\Git\auto_invest` and run:

   ```
   uv run python scripts/build_quantconnect_project.py
   ```

   Why: it copies the rubric byte for byte and turns the two TOML files into `settings_snapshot.py`, which the web editor can hold.

   Success: three lines, `wrote 13 files to …`, `rubric sha256 …`, `git commit …`. Copy the first eight characters of the hash and the commit into a scratch note; the research log needs both.

## B. Create the project (first run only)

2. Go to https://www.quantconnect.com/ and sign in.
3. Open the algorithm lab from the left menu and click the button to create a new project. Choose **Python** and name it `auto_invest`.

   Why: one project per strategy; every year's run reuses it.

   Success: the editor opens with a `main.py` containing a sample algorithm.

4. In the file panel, use the new-folder control to add a folder named exactly `rubric`.

   Why: the rubric files use relative imports, so they must sit in a folder with an `__init__.py`, never loose.

   Success: an empty `rubric` folder appears under the project.

5. Inside `rubric`, add one file per file in `build\quantconnect\rubric\`, with the identical name, and paste each file's full contents. Do `__init__.py` first.

   Success: nine files under `rubric`, names matching the folder on disk exactly.

6. At the project root, add `lean_adapter.py`, `settings.py`, and `settings_snapshot.py` and paste each from `build\quantconnect\`.
7. Open the project's `main.py`, select all, delete, and paste `build\quantconnect\main.py`.

   Success: the project shows 13 files. Nothing else.

## C. Run one in-sample year

8. In `main.py`, find `IN_SAMPLE_YEAR = 2019` near the top. For the baseline leave it at 2019; for later years change only that number.

   Flag: never type 2025 or later. The algorithm will refuse, but the rule is yours, not the code's.

9. Click **Build**, then **Backtest**.

   Why: Build compiles; Backtest runs on the free node.

   Success: the backtest page opens and the equity chart starts drawing. A one-year run takes roughly 30 minutes.

10. Open the **Logs** tab. The first lines read `rubric 0.1.0 sha256 …` and `object store max size … bytes`.

    Success: the first eight characters of the hash match your scratch note. If they do not, stop: a rubric file was pasted wrong. Re-paste the folder and run again.

11. When the run finishes, read the last three log lines: `decisions N saved to object store key …`, `rejections {…}`, `orders N`.

    Success: `orders` is under 10,000 and `decisions` is in the tens of thousands. Copy the `rejections` line and the object store key to the scratch note.

12. On the **Overview** tab note Total Trades, Net Profit, and Drawdown.

## D. Download the evidence

13. On the backtest page open the **Orders** tab and use its download control to save the orders list next to your scratch note.

    Why: Phase 3 needs the trade list.

14. From the top-right organization menu open **Object Store**, find the key from step 11, and download `decisions.jsonl`.
15. Count rejections locally:

    ```
    uv run python scripts/count_rejections.py <path to decisions.jsonl>
    ```

    Success: the counts match the `rejections` log line.

## E. Record the run

16. Add one row to `docs/research-log.md`: today's date, the year, "baseline" (or what changed), the eight-character hash, trades, net return, max drawdown, the top rejecting check and its count.
17. Commit the research log:

    ```
    git add docs/research-log.md
    git commit -m "docs: research log, <year> <what changed>"
    ```

## Every later variation

Change the repo, commit, run section A, re-paste only the files whose contents changed (the build prints nothing about that, so compare in the editor), then sections C to E. If the rubric changed, step 10's hash changes too and the research log records the new one.
```

- [ ] **Step 3: Tick the build plan**

In `docs/build-plan.md`, in the Phase 2 "You do" and "Checklist" sections, change `- [ ]` to `- [x]` for: decide the hold-out, write the ADR, read the ORB example, thin LEAN wrapper, copy the rubric files (the build script and runbook), Interactive Brokers brokerage model, entry window and orders, and the research log. Leave "Baseline backtest on the in-sample years only" and "Export daily returns and the trade list" unticked until Task 11.

- [ ] **Step 4: Commit**

```bash
git add docs/research-log.md docs/runbooks/quantconnect-baseline-backtest.md docs/build-plan.md
git commit -m "docs: research log, QuantConnect runbook, Phase 2 checklist"
```

---

### Task 11: Cloud baseline run (Chris performs, Claude records)

**Files:**
- Modify: `docs/research-log.md`
- Modify: `docs/build-plan.md` (the last two Phase 2 ticks)
- Possibly modify: `src/auto_invest/adapters/lean/main.py` if the cloud run reports an error

- [ ] **Step 1: Chris runs sections A to D of the runbook for `IN_SAMPLE_YEAR = 2019`**

Expected: the hash in the log matches the build output; the run completes; `orders` under 10,000.

If the Build step or the run fails, paste the error text into the session. The likely causes, in order: a mis-pasted file (hash mismatch, step 10), a LEAN attribute name (fix in `main.py`, rebuild, re-paste `main.py` only, commit as `fix: …`), or the Object Store quota (compare the `max size` log line with the file size; if the file does not fit, report back before changing anything, because the fix is a smaller log line, not fewer decisions).

- [ ] **Step 2: Verify the exit criteria from the orders list**

With the downloaded orders file, confirm: every buy fill is followed by a stop-market order for the same quantity; no fill time is after 15:50 except forced-close fills; no position is open at the end of any day (every buy quantity is matched by sells the same day).

- [ ] **Step 3: Record the run**

Add the research-log row (runbook section E). Tick the last two Phase 2 checklist items in `docs/build-plan.md`. Commit:

```bash
git add docs/research-log.md docs/build-plan.md
git commit -m "docs: baseline 2019 run recorded"
```

Phase 2 is done when this commit exists and every Phase 2 exit criterion in the build plan is met. Later years (2020 to 2024) are further rows, run the same way.
