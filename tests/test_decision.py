import json
from datetime import timedelta

from auto_invest.rubric import RUBRIC_VERSION
from auto_invest.rubric.decision import decide
from auto_invest.rubric.records import (
    AccountState,
    Candidate,
    InstrumentStatus,
    MarketData,
    Quote,
    Sale,
    SettlementLedger,
)
from conftest import DAY, daily_bars, history_bars, minute_bars, ts


def good_inputs():
    candidate = Candidate("SPY", 100.5, 98.49, ts(10, 30))
    market = MarketData(
        Quote("SPY", 100.49, 100.51, ts(10, 30)),
        minute_bars(count=61, open=100.0, step=0.01, volume=40000.0),
        history_bars(open=100.0, step=0.002, volume=20000.0),
        daily_bars(start_price=74.2, step=0.1),
    )
    instrument = InstrumentStatus("SPY", True, False)
    account = AccountState(5000.0, (), 0, 0.0, 0.0, True, True, ts(10, 30), settled_cash=5000.0)
    ledger = SettlementLedger(5000.0, 0.0, ())
    return candidate, market, instrument, account, ledger


def test_a_good_candidate_is_accepted(settings):
    record = decide(*good_inputs(), settings)
    assert record.verdict == "accepted"
    assert record.rejected_by is None
    assert record.rubric_version == RUBRIC_VERSION
    assert record.symbol == "SPY"
    assert len(record.checks) == 8
    assert all(check.passed for check in record.checks)
    assert record.score.passed
    assert record.size.shares == 12


def test_rejected_by_names_the_first_failing_check(settings):
    candidate, market, instrument, account, ledger = good_inputs()
    halted = InstrumentStatus("SPY", True, True)
    record = decide(candidate, market, halted, account, ledger, settings)
    assert record.verdict == "rejected"
    assert record.rejected_by == "instrument_is_eligible"
    assert len(record.checks) == 8


def test_rejected_by_signal_score_when_checks_pass(settings):
    candidate, market, instrument, account, ledger = good_inputs()
    weak = MarketData(market.quote, market.today_bars, market.history_bars, daily_bars(start_price=126.0, step=-0.1))
    strict = settings.model_copy(update={"score_threshold": 0.99})
    record = decide(candidate, weak, instrument, account, ledger, strict)
    assert record.verdict == "rejected"
    assert record.rejected_by == "signal_score"


def test_unsettled_proceeds_cannot_be_spent_today(settings):
    candidate, market, instrument, account, ledger = good_inputs()
    poor = AccountState(5000.0, (), 0, 0.0, 0.0, True, True, ts(10, 30), settled_cash=None)
    unsettled = SettlementLedger(50.0, 0.0, (Sale(DAY, 4950.0),))
    record = decide(candidate, market, instrument, poor, unsettled, settings)
    assert record.verdict == "rejected"
    assert record.size.shares == 0
    assert record.rejected_by == "trade_beats_its_costs"
    tomorrow = Candidate("SPY", 100.5, 98.49, ts(10, 30, day=DAY + timedelta(days=1)))
    later_ledger = SettlementLedger(50.0, 0.0, (Sale(DAY, 4950.0),))
    settled = decide(tomorrow, market, instrument, poor, later_ledger, settings)
    assert settled.size.shares == 12


def test_all_inputs_missing_still_records_all_eight_checks(settings):
    record = decide(None, None, None, None, None, settings)
    assert record.verdict == "rejected"
    assert record.rejected_by == "data_is_sane"
    assert [c.name for c in record.checks][0] == "data_is_sane"
    assert all(not c.passed for c in record.checks)
    assert record.symbol is None
    assert record.timestamp is None


def test_record_round_trips_through_json(settings):
    record = decide(*good_inputs(), settings)
    as_dict = record.to_dict()
    text = json.dumps(as_dict)
    back = json.loads(text)
    assert back["verdict"] == "accepted"
    assert back["timestamp"] == ts(10, 30).isoformat()
    assert isinstance(back["checks"], list)
    assert back["checks"][0]["name"] == "data_is_sane"
    assert back["score"]["components"][0]["name"] == "trend_direction"
    assert back["size"]["shares"] == 12


def test_a_rejected_record_reads_in_plain_words(settings):
    candidate, market, instrument, account, ledger = good_inputs()
    losing = AccountState(5000.0, (), 0, -30.0, -25.0, True, True, ts(10, 30), settled_cash=5000.0)
    record = decide(candidate, market, instrument, losing, ledger, settings).to_dict()
    failed = [c for c in record["checks"] if not c["passed"]]
    assert failed == [
        {
            "name": "daily_loss_limit_not_hit",
            "passed": False,
            "reason": "today's P&L -55.00 against the halt at -50.00",
        }
    ]
    assert record["rejected_by"] == "daily_loss_limit_not_hit"
