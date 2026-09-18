import json
from dataclasses import FrozenInstanceError, asdict

import pytest

from auto_invest.rubric.records import (
    AccountState,
    Candidate,
    Position,
    Quote,
    first_missing,
)
from conftest import ts


def test_records_are_frozen_and_hashable():
    quote = Quote("SPY", 100.0, 100.02, ts(10, 30))
    with pytest.raises(FrozenInstanceError):
        quote.bid = 1.0
    assert hash(quote) == hash(Quote("SPY", 100.0, 100.02, ts(10, 30)))
    assert quote == Quote("SPY", 100.0, 100.02, ts(10, 30))


def test_optional_defaults_only_where_the_spec_allows():
    position = Position("SPY", 1, 100.0)
    assert position.stop_price is None
    account = AccountState(5000.0, (), 0, 0.0, 0.0, True, True, ts(10, 30))
    assert account.settled_cash is None
    with pytest.raises(TypeError):
        Candidate("SPY", 100.0, 99.0)


def test_first_missing_names_the_record_and_field():
    assert first_missing("Quote", None, "bid") == "missing: Quote"
    quote = Quote("SPY", None, 100.02, ts(10, 30))
    assert first_missing("Quote", quote, "bid", "ask") == "missing: Quote.bid"
    assert first_missing("Quote", quote, "ask") is None


def test_records_serialise_to_json():
    account = AccountState(5000.0, (Position("SPY", 1, 100.0),), 0, 0.0, 0.0, True, True, None)
    assert json.loads(json.dumps(asdict(account)))["positions"][0]["symbol"] == "SPY"
