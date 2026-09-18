import pytest
from datetime import timedelta

from auto_invest.rubric.checks import (
    CHECK_NAMES,
    daily_loss_limit_not_hit,
    data_is_sane,
    exit_is_defined,
    instrument_is_eligible,
    market_is_liquid,
    risk_budget_has_room,
    run_checks,
    system_is_healthy,
    trade_beats_its_costs,
)
from auto_invest.rubric.records import (
    AccountState,
    Bar,
    Candidate,
    InstrumentStatus,
    MarketData,
    Position,
    Quote,
)
from auto_invest.rubric.sizing import Size
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


def test_risk_budget_has_room_fails_on_an_incomplete_position(settings):
    held = (Position("QQQ", None, 100.0),)
    result = risk_budget_has_room(size(), candidate(), account(positions=held), 5000.0, settings)
    assert not result.passed
    assert result.reason == "missing: Position.quantity"


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
        (candidate(), account(positions=(None,)), "missing: Position"),
        (candidate(), account(positions=(Position("SPY", None, 100.0),)), "missing: Position.quantity"),
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
