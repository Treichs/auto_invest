from dataclasses import asdict, dataclass
from datetime import datetime

from . import RUBRIC_VERSION
from .bars import local
from .checks import CheckResult, run_checks
from .records import AccountState, Candidate, InstrumentStatus, MarketData, SettlementLedger
from .score import SignalScore, components, signal_score
from .settlement import available_settled_cash
from .sizing import Size, position_size


@dataclass(frozen=True)
class DecisionRecord:
    rubric_version: str
    symbol: str | None
    timestamp: datetime | None
    checks: tuple[CheckResult, ...]
    score: SignalScore | None
    size: Size | None
    verdict: str
    rejected_by: str | None

    def to_dict(self) -> dict:
        return {
            "rubric_version": self.rubric_version,
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "checks": [asdict(check) for check in self.checks],
            "score": None
            if self.score is None
            else {**asdict(self.score), "components": [asdict(c) for c in self.score.components]},
            "size": None if self.size is None else asdict(self.size),
            "verdict": self.verdict,
            "rejected_by": self.rejected_by,
        }


def decide(
    candidate: Candidate | None,
    market: MarketData | None,
    instrument: InstrumentStatus | None,
    account: AccountState | None,
    ledger: SettlementLedger | None,
    settings,
) -> DecisionRecord:
    usable_cash = None
    if candidate is not None and candidate.timestamp is not None:
        on_date = local(candidate.timestamp, settings.timezone).date()
        usable_cash = available_settled_cash(ledger, account, on_date)
    size = position_size(candidate, account, usable_cash, settings)
    checks = run_checks(candidate, market, instrument, account, usable_cash, size, settings)
    score = signal_score(components(candidate, market, settings), settings)
    failed = next((check.name for check in checks if not check.passed), None)
    if failed:
        rejected_by = failed
    elif not score.passed:
        rejected_by = "signal_score"
    elif size.shares < 1:
        rejected_by = "position_size"
    else:
        rejected_by = None
    return DecisionRecord(
        RUBRIC_VERSION,
        candidate.symbol if candidate else None,
        candidate.timestamp if candidate else None,
        checks,
        score,
        size,
        "rejected" if rejected_by else "accepted",
        rejected_by,
    )
