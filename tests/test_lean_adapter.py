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
