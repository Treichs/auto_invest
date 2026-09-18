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


def test_incomplete_position_gives_zero_shares_with_reason(settings):
    held = (Position("QQQ", None, 100.0),)
    size = position_size(candidate(100.0, 98.0), account(positions=held), 5000.0, settings)
    assert size.shares == 0
    assert size.reason == "missing: Position.quantity"
    held = (Position("QQQ", 30, None),)
    assert (
        position_size(candidate(100.0, 98.0), account(positions=held), 5000.0, settings).reason
        == "missing: Position.average_price"
    )
