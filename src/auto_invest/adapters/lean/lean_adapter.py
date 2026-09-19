from datetime import date, datetime
from typing import Iterable
from zoneinfo import ZoneInfo

from rubric.records import Bar, InstrumentStatus, Quote

TIMEZONE = "America/New_York"
NEW_YORK = ZoneInfo(TIMEZONE)


def aware(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=NEW_YORK)
    return moment.astimezone(NEW_YORK)


def to_bar(symbol: str, trade_bar) -> Bar:
    return Bar(
        symbol,
        aware(trade_bar.time),
        float(trade_bar.open),
        float(trade_bar.high),
        float(trade_bar.low),
        float(trade_bar.close),
        float(trade_bar.volume),
    )


def to_quote(symbol: str, quote_bar) -> Quote:
    if quote_bar is None or quote_bar.bid is None or quote_bar.ask is None:
        return Quote(symbol, None, None, None)
    return Quote(symbol, float(quote_bar.bid.close), float(quote_bar.ask.close), aware(quote_bar.end_time))


def instrument_status(symbol: str, trade_bar, listed_in_us: bool) -> InstrumentStatus:
    halted = trade_bar is None or bool(trade_bar.is_fill_forward)
    return InstrumentStatus(symbol, listed_in_us, halted)


class SessionStore:
    def __init__(self, history_sessions: int):
        self.history_sessions = history_sessions
        self.session_date: date | None = None
        self.today: list[Bar] = []
        self.sessions: dict[date, tuple[Bar, ...]] = {}
        self.daily: tuple[Bar, ...] = ()

    def add(self, bar: Bar, fill_forward: bool) -> None:
        if fill_forward:
            return
        day = bar.start.date()
        if day != self.session_date:
            self._roll(day)
        self.today.append(bar)

    def _roll(self, day: date) -> None:
        if self.session_date is not None and self.today:
            self.sessions[self.session_date] = tuple(self.today)
            while len(self.sessions) > self.history_sessions:
                del self.sessions[min(self.sessions)]
        self.session_date = day
        self.today = []

    def set_daily(self, bars: Iterable[Bar], today: date) -> None:
        self.daily = tuple(bar for bar in bars if bar.start.date() < today)

    def today_bars(self) -> tuple[Bar, ...]:
        return tuple(self.today)

    def history_bars(self) -> tuple[Bar, ...]:
        return tuple(bar for day in sorted(self.sessions) for bar in self.sessions[day])
