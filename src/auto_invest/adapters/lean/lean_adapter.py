from datetime import datetime
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
