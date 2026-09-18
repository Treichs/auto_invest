from dataclasses import dataclass

from .bars import local, volume_until
from .costs import total_cost_round_trip
from .records import AccountState, Candidate, InstrumentStatus, MarketData, first_missing
from .sizing import Size, current_exposure


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
    if last_close <= 0:
        return CheckResult(name, False, f"last close {last_close} is not a valid price")
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
    if quote.bid <= 0 or quote.ask < quote.bid:
        return CheckResult(name, False, f"bid {quote.bid} and ask {quote.ask} are not a valid market")
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


def trade_beats_its_costs(
    size: Size | None, candidate: Candidate | None, market: MarketData | None, settings
) -> CheckResult:
    name = "trade_beats_its_costs"
    reason = (
        first_missing("Size", size)
        or first_missing("Candidate", candidate, "entry_price")
        or _quote_missing(market)
    )
    if reason:
        return CheckResult(name, False, reason)
    if size.shares < 1:
        return CheckResult(name, False, "no shares to trade")
    if size.risk_at_shares <= 0:
        return CheckResult(name, False, "no amount at risk")
    cost = total_cost_round_trip(size.shares, candidate.entry_price, market.quote)
    fraction = cost / size.risk_at_shares
    limit = settings.max_cost_fraction_of_risk
    verdict = fraction <= limit
    return CheckResult(
        name,
        verdict,
        f"round-trip cost {cost:.2f} is {fraction:.1%} of risk {size.risk_at_shares:.2f}, limit {limit:.0%}",
    )


def exit_is_defined(candidate: Candidate | None, settings) -> CheckResult:
    name = "exit_is_defined"
    reason = first_missing("Candidate", candidate, "entry_price", "stop_price")
    if reason:
        return CheckResult(name, False, reason)
    if not 0 < candidate.stop_price < candidate.entry_price:
        return CheckResult(
            name, False, f"stop {candidate.stop_price} is not below entry {candidate.entry_price}"
        )
    return CheckResult(name, True, f"stop {candidate.stop_price} below entry {candidate.entry_price}")


def risk_budget_has_room(
    size: Size | None,
    candidate: Candidate | None,
    account: AccountState | None,
    usable_cash: float | None,
    settings,
) -> CheckResult:
    name = "risk_budget_has_room"
    reason = (
        first_missing("Size", size)
        or first_missing("Candidate", candidate, "entry_price")
        or first_missing("AccountState", account, "start_of_day_equity", "positions", "entries_today")
    )
    if reason:
        return CheckResult(name, False, reason)
    for position in account.positions:
        reason = first_missing("Position", position, "quantity", "average_price")
        if reason:
            return CheckResult(name, False, reason)
    if usable_cash is None:
        return CheckResult(name, False, "missing: usable settled cash")
    if size.shares < 1:
        return CheckResult(name, False, "no shares to trade")
    equity = account.start_of_day_equity
    order_value = size.shares * candidate.entry_price
    exposure = current_exposure(account)
    limits = [
        (order_value > settings.order_value_cap * equity, f"order value {order_value:.2f} is over the order value cap {settings.order_value_cap * equity:.2f}"),
        (order_value > settings.per_symbol_cap * equity, f"order value {order_value:.2f} is over the per-symbol cap {settings.per_symbol_cap * equity:.2f}"),
        (exposure + order_value > settings.total_exposure_cap * equity, f"exposure {exposure + order_value:.2f} would be over the total exposure cap {settings.total_exposure_cap * equity:.2f}"),
        (account.entries_today >= settings.entries_per_day, f"entries today {account.entries_today} has reached the cap {settings.entries_per_day}"),
        (order_value > usable_cash, f"order value {order_value:.2f} is over usable settled cash {usable_cash:.2f}"),
    ]
    for failed, message in limits:
        if failed:
            return CheckResult(name, False, message)
    return CheckResult(
        name,
        True,
        f"order value {order_value:.2f}, exposure after {exposure + order_value:.2f}, entry {account.entries_today + 1} of {settings.entries_per_day}, settled cash {usable_cash:.2f}",
    )


def daily_loss_limit_not_hit(account: AccountState | None, settings) -> CheckResult:
    name = "daily_loss_limit_not_hit"
    reason = first_missing(
        "AccountState", account, "start_of_day_equity", "realised_pnl_today", "unrealised_pnl_today"
    )
    if reason:
        return CheckResult(name, False, reason)
    pnl = account.realised_pnl_today + account.unrealised_pnl_today
    limit = -settings.daily_loss_limit * account.start_of_day_equity
    return CheckResult(
        name, pnl > limit, f"today's P&L {pnl:.2f} against the halt at {limit:.2f}"
    )


def system_is_healthy(candidate: Candidate | None, account: AccountState | None, settings) -> CheckResult:
    name = "system_is_healthy"
    reason = first_missing("Candidate", candidate, "symbol", "timestamp") or first_missing(
        "AccountState", account, "broker_connected", "positions_reconciled", "positions"
    )
    if reason:
        return CheckResult(name, False, reason)
    for position in account.positions:
        reason = first_missing("Position", position, "symbol", "quantity")
        if reason:
            return CheckResult(name, False, reason)
    if not account.broker_connected:
        return CheckResult(name, False, "broker not connected")
    if not account.positions_reconciled:
        return CheckResult(name, False, "positions not reconciled with the broker")
    if any(p.symbol == candidate.symbol and p.quantity for p in account.positions):
        return CheckResult(name, False, f"already holding {candidate.symbol}")
    at = local(candidate.timestamp, settings.timezone).time()
    if not settings.entry_window_start <= at < settings.entry_window_end:
        return CheckResult(
            name,
            False,
            f"{at:%H:%M} is outside the entry window {settings.entry_window_start:%H:%M} to {settings.entry_window_end:%H:%M}",
        )
    return CheckResult(name, True, f"connected, reconciled, flat in {candidate.symbol}, {at:%H:%M} inside the window")


CHECK_NAMES = (
    "data_is_sane",
    "instrument_is_eligible",
    "market_is_liquid",
    "trade_beats_its_costs",
    "exit_is_defined",
    "risk_budget_has_room",
    "daily_loss_limit_not_hit",
    "system_is_healthy",
)


def run_checks(
    candidate, market, instrument, account, usable_cash, size, settings
) -> tuple[CheckResult, ...]:
    return (
        data_is_sane(candidate, market, settings),
        instrument_is_eligible(instrument, settings),
        market_is_liquid(candidate, market, settings),
        trade_beats_its_costs(size, candidate, market, settings),
        exit_is_defined(candidate, settings),
        risk_budget_has_room(size, candidate, account, usable_cash, settings),
        daily_loss_limit_not_hit(account, settings),
        system_is_healthy(candidate, account, settings),
    )
