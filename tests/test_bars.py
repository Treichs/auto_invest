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
