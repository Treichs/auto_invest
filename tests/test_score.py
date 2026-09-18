from datetime import time, timedelta

import pytest

from auto_invest.rubric.records import Bar, Candidate, MarketData, Quote
from auto_invest.rubric.score import (
    ComponentScore,
    components,
    intraday_momentum,
    opening_range_breakout,
    relative_volume,
    signal_score,
    trend_direction,
    volatility_and_volume_conditions,
)
from conftest import DAY, daily_bars, history_bars, minute_bars, ts


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


def test_trend_direction_fails_on_a_zero_close(settings):
    bars = daily_bars()
    zero = bars[:-1] + (Bar("SPY", bars[-1].start, 0.0, 0.0, 0.0, 0.0, 1.0),)
    result = trend_direction(market(daily=zero), settings)
    assert result.value == 0.0
    assert "not a valid price" in result.reason


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


def test_intraday_momentum_with_a_zero_open_scores_zero(settings):
    today = minute_bars(count=61, open=0.0, step=0.0)
    result = intraday_momentum(candidate(), market(today=today), settings)
    assert result.value == 0.0
    assert "missing" in result.reason


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
