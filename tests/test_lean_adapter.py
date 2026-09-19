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
