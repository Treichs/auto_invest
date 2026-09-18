import math
from dataclasses import dataclass

from .records import AccountState, Candidate, first_missing


@dataclass(frozen=True)
class Size:
    budget: float
    shares: int
    risk_at_budget: float
    risk_at_shares: float
    reason: str | None = None


NO_SIZE = Size(0.0, 0, 0.0, 0.0)


def current_exposure(account: AccountState) -> float:
    return sum(
        position.quantity * position.average_price
        for position in account.positions
        if position.quantity is not None and position.average_price is not None
    )


def position_size(
    candidate: Candidate | None,
    account: AccountState | None,
    usable_cash: float | None,
    settings,
) -> Size:
    reason = first_missing("Candidate", candidate, "entry_price", "stop_price") or first_missing(
        "AccountState", account, "start_of_day_equity", "positions"
    )
    if reason:
        return Size(0.0, 0, 0.0, 0.0, reason)
    if usable_cash is None:
        return Size(0.0, 0, 0.0, 0.0, "missing: usable settled cash")
    entry, stop = candidate.entry_price, candidate.stop_price
    if entry <= 0 or not 0 < stop < entry:
        return Size(0.0, 0, 0.0, 0.0, f"stop {stop} is not below entry {entry}")
    equity = account.start_of_day_equity
    stop_fraction = (entry - stop) / entry
    budget = min(
        settings.risk_per_trade * equity / stop_fraction,
        settings.per_symbol_cap * equity,
        settings.total_exposure_cap * equity - current_exposure(account),
        usable_cash,
    )
    budget = max(budget, 0.0)
    shares = math.floor(round(budget / entry, 9))
    return Size(budget, shares, budget * stop_fraction, shares * (entry - stop))
