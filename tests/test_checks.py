import pytest
from datetime import timedelta

from auto_invest.rubric.checks import (
    data_is_sane,
    instrument_is_eligible,
    market_is_liquid,
)
from auto_invest.rubric.records import Bar, Candidate, InstrumentStatus, MarketData, Quote
from conftest import DAY, daily_bars, minute_bars, ts


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


def test_data_is_sane_fails_on_a_zero_last_close(settings):
    zero = (Bar("SPY", ts(9, 30, day=DAY - timedelta(days=1)), 0.0, 0.0, 0.0, 0.0, 1.0),)
    result = data_is_sane(candidate(), market(daily=zero), settings)
    assert not result.passed
    assert "not a valid price" in result.reason


def test_market_is_liquid_fails_on_a_zero_quote(settings):
    result = market_is_liquid(candidate(), market(q=quote(bid=0.0, ask=0.0)), settings)
    assert not result.passed
    assert "not a valid market" in result.reason
