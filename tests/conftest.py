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
