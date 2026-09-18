from datetime import date, timedelta

from .records import AccountState, SettlementLedger, first_missing


def settlement_date(trade_date: date) -> date:
    settled = trade_date + timedelta(days=1)
    while settled.weekday() >= 5:
        settled += timedelta(days=1)
    return settled


def usable_settled_cash(ledger: SettlementLedger | None, on_date: date) -> float | None:
    if first_missing("SettlementLedger", ledger, "start_of_day_settled_cash", "buys_today"):
        return None
    settled = sum(
        sale.proceeds
        for sale in ledger.sales or ()
        if sale.trade_date is not None
        and sale.proceeds is not None
        and settlement_date(sale.trade_date) <= on_date
    )
    return ledger.start_of_day_settled_cash - ledger.buys_today + settled


def available_settled_cash(
    ledger: SettlementLedger | None, account: AccountState | None, on_date: date
) -> float | None:
    from_ledger = usable_settled_cash(ledger, on_date)
    if from_ledger is None:
        return None
    if account is None or account.settled_cash is None:
        return from_ledger
    return min(from_ledger, account.settled_cash)
