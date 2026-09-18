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
