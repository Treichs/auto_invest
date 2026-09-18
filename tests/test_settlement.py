from datetime import date

from auto_invest.rubric.records import AccountState, Sale, SettlementLedger
from auto_invest.rubric.settlement import (
    available_settled_cash,
    settlement_date,
    usable_settled_cash,
)

FRI = date(2026, 9, 11)
SAT = date(2026, 9, 12)
SUN = date(2026, 9, 13)
MON = date(2026, 9, 14)
TUE = date(2026, 9, 15)


def test_settlement_is_the_next_weekday():
    assert settlement_date(MON) == TUE
    assert settlement_date(FRI) == MON


def test_friday_sale_is_usable_from_monday():
    ledger = SettlementLedger(1000.0, 0.0, (Sale(FRI, 500.0),))
    assert usable_settled_cash(ledger, FRI) == 1000.0
    assert usable_settled_cash(ledger, SAT) == 1000.0
    assert usable_settled_cash(ledger, SUN) == 1000.0
    assert usable_settled_cash(ledger, MON) == 1500.0


def test_buys_today_reduce_usable_cash():
    ledger = SettlementLedger(1000.0, 400.0, ())
    assert usable_settled_cash(ledger, MON) == 600.0


def test_sales_with_missing_fields_are_ignored():
    ledger = SettlementLedger(1000.0, 0.0, (Sale(None, 500.0), Sale(FRI, None)))
    assert usable_settled_cash(ledger, TUE) == 1000.0


def test_missing_ledger_or_field_gives_none():
    assert usable_settled_cash(None, MON) is None
    assert usable_settled_cash(SettlementLedger(None, 0.0, ()), MON) is None
    assert usable_settled_cash(SettlementLedger(1000.0, None, ()), MON) is None


def account_with(settled_cash):
    return AccountState(5000.0, (), 0, 0.0, 0.0, True, True, None, settled_cash=settled_cash)


def test_available_is_the_lower_of_ledger_and_broker():
    ledger = SettlementLedger(1000.0, 0.0, ())
    assert available_settled_cash(ledger, account_with(800.0), MON) == 800.0
    assert available_settled_cash(ledger, account_with(1200.0), MON) == 1000.0
    assert available_settled_cash(ledger, account_with(None), MON) == 1000.0
    assert available_settled_cash(ledger, None, MON) == 1000.0
    assert available_settled_cash(None, account_with(800.0), MON) is None
