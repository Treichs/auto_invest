from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class Quote:
    symbol: str | None
    bid: float | None
    ask: float | None
    timestamp: datetime | None


@dataclass(frozen=True)
class Bar:
    symbol: str | None
    start: datetime | None
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: float | None


@dataclass(frozen=True)
class InstrumentStatus:
    symbol: str | None
    listed_in_us: bool | None
    halted: bool | None


@dataclass(frozen=True)
class Position:
    symbol: str | None
    quantity: float | None
    average_price: float | None
    stop_price: float | None = None


@dataclass(frozen=True)
class AccountState:
    start_of_day_equity: float | None
    positions: tuple[Position, ...] | None
    entries_today: int | None
    realised_pnl_today: float | None
    unrealised_pnl_today: float | None
    broker_connected: bool | None
    positions_reconciled: bool | None
    timestamp: datetime | None
    settled_cash: float | None = None


@dataclass(frozen=True)
class Sale:
    trade_date: date | None
    proceeds: float | None


@dataclass(frozen=True)
class SettlementLedger:
    start_of_day_settled_cash: float | None
    buys_today: float | None
    sales: tuple[Sale, ...] | None


@dataclass(frozen=True)
class Candidate:
    symbol: str | None
    entry_price: float | None
    stop_price: float | None
    timestamp: datetime | None


@dataclass(frozen=True)
class MarketData:
    quote: Quote | None
    today_bars: tuple[Bar, ...] | None
    history_bars: tuple[Bar, ...] | None
    daily_bars: tuple[Bar, ...] | None


def first_missing(label: str, record, *names: str) -> str | None:
    if record is None:
        return f"missing: {label}"
    for name in names:
        if getattr(record, name) is None:
            return f"missing: {label}.{name}"
    return None
