from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from .records import Bar


def local(moment: datetime, timezone: str) -> datetime:
    return moment.astimezone(ZoneInfo(timezone))


def bars_in_window(bars, start: time, end: time, timezone: str) -> tuple[Bar, ...]:
    return tuple(
        bar
        for bar in bars or ()
        if bar.start is not None and start <= local(bar.start, timezone).time() < end
    )


def by_session(bars, timezone: str) -> dict[date, tuple[Bar, ...]]:
    grouped: dict[date, list[Bar]] = {}
    for bar in bars or ():
        if bar.start is None:
            continue
        grouped.setdefault(local(bar.start, timezone).date(), []).append(bar)
    return {day: tuple(grouped[day]) for day in sorted(grouped)}


def volume_until(bars, until: time, timezone: str) -> float:
    return sum(
        bar.volume
        for bar in bars or ()
        if bar.start is not None
        and bar.volume is not None
        and local(bar.start, timezone).time() < until
    )


def complete(bars, *fields: str) -> bool:
    if not bars:
        return False
    return all(getattr(bar, field) is not None for bar in bars for field in fields)
