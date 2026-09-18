from dataclasses import dataclass

from .bars import local, volume_until
from .records import Candidate, InstrumentStatus, MarketData, first_missing


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    reason: str


def _quote_missing(market: MarketData | None) -> str | None:
    return first_missing("MarketData", market, "quote") or first_missing(
        "Quote", market.quote, "bid", "ask", "timestamp"
    )


def data_is_sane(candidate: Candidate | None, market: MarketData | None, settings) -> CheckResult:
    name = "data_is_sane"
    reason = first_missing("Candidate", candidate, "timestamp") or _quote_missing(market)
    if reason:
        return CheckResult(name, False, reason)
    if not market.daily_bars:
        return CheckResult(name, False, "missing: MarketData.daily_bars")
    last_close = market.daily_bars[-1].close
    if last_close is None:
        return CheckResult(name, False, "missing: Bar.close")
    quote = market.quote
    age = (candidate.timestamp - quote.timestamp).total_seconds()
    if age > settings.quote_max_age_seconds:
        return CheckResult(
            name, False, f"quote is {age:.1f}s old, limit {settings.quote_max_age_seconds}s"
        )
    if quote.bid <= 0 or quote.ask < quote.bid:
        return CheckResult(name, False, f"bid {quote.bid} and ask {quote.ask} are not a valid market")
    mid = (quote.bid + quote.ask) / 2
    band = settings.price_band
    if abs(mid / last_close - 1) > band:
        return CheckResult(
            name, False, f"mid {mid:.2f} is outside ±{band:.0%} of last close {last_close:.2f}"
        )
    return CheckResult(
        name, True, f"quote {age:.1f}s old, mid {mid:.2f} within ±{band:.0%} of {last_close:.2f}"
    )


def instrument_is_eligible(instrument: InstrumentStatus | None, settings) -> CheckResult:
    name = "instrument_is_eligible"
    reason = first_missing("InstrumentStatus", instrument, "symbol", "listed_in_us", "halted")
    if reason:
        return CheckResult(name, False, reason)
    if not instrument.listed_in_us:
        return CheckResult(name, False, f"{instrument.symbol} is not US-listed")
    if instrument.halted:
        return CheckResult(name, False, f"{instrument.symbol} is halted")
    if instrument.symbol not in settings.approved_symbols:
        return CheckResult(name, False, f"{instrument.symbol} is not on the approved list")
    return CheckResult(name, True, f"{instrument.symbol} is US-listed, trading, and approved")


def market_is_liquid(candidate: Candidate | None, market: MarketData | None, settings) -> CheckResult:
    name = "market_is_liquid"
    reason = first_missing("Candidate", candidate, "timestamp") or _quote_missing(market)
    if reason:
        return CheckResult(name, False, reason)
    if not market.today_bars:
        return CheckResult(name, False, "missing: MarketData.today_bars")
    quote = market.quote
    mid = (quote.bid + quote.ask) / 2
    spread = (quote.ask - quote.bid) / mid
    if spread > settings.spread_cap:
        return CheckResult(name, False, f"spread {spread:.4%} is over the cap {settings.spread_cap:.4%}")
    until = local(candidate.timestamp, settings.timezone).time()
    volume = volume_until(market.today_bars, until, settings.timezone)
    if volume < settings.volume_floor:
        return CheckResult(
            name, False, f"volume {volume:,.0f} so far is under the floor {settings.volume_floor:,.0f}"
        )
    return CheckResult(name, True, f"spread {spread:.4%}, volume {volume:,.0f} so far")
