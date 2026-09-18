from dataclasses import dataclass
from datetime import datetime, time, timedelta
from statistics import pstdev

from .bars import bars_in_window, by_session, complete, local, volume_until
from .records import Bar, Candidate, MarketData, first_missing

OPEN = time(9, 30)
FIRST_HALF_HOUR_END = time(10, 0)
LOOKBACKS = (21, 63, 126, 252)


@dataclass(frozen=True)
class ComponentScore:
    name: str
    value: float
    reason: str


def clip(value: float) -> float:
    return max(0.0, min(1.0, value))


def recent_sessions(
    market: MarketData | None, candidate: Candidate | None, settings
) -> tuple[tuple[Bar, ...], ...]:
    if market is None or candidate is None or candidate.timestamp is None:
        return ()
    today = local(candidate.timestamp, settings.timezone).date()
    sessions = by_session(market.history_bars, settings.timezone)
    before = [bars for day, bars in sessions.items() if day < today]
    if len(before) < settings.history_sessions:
        return ()
    return tuple(before[-settings.history_sessions :])


def trend_direction(market: MarketData | None, settings) -> ComponentScore:
    name = "trend_direction"
    reason = first_missing("MarketData", market)
    if reason:
        return ComponentScore(name, 0.0, reason)
    needed = max(LOOKBACKS) + 1
    if not market.daily_bars or len(market.daily_bars) < needed:
        return ComponentScore(name, 0.0, f"missing: MarketData.daily_bars needs {needed} closes")
    if not complete(market.daily_bars, "close"):
        return ComponentScore(name, 0.0, "missing: Bar.close")
    closes = [bar.close for bar in market.daily_bars]
    if min(closes) <= 0:
        return ComponentScore(name, 0.0, "a daily close is not a valid price")
    returns = [closes[-1] / closes[-1 - lookback] - 1 for lookback in LOOKBACKS]
    positive = sum(1 for r in returns if r > 0)
    return ComponentScore(
        name, positive / len(LOOKBACKS), f"{positive} of {len(LOOKBACKS)} lookbacks positive"
    )


def opening_range_breakout(
    candidate: Candidate | None, market: MarketData | None, settings
) -> ComponentScore:
    name = "opening_range_breakout"
    reason = first_missing("Candidate", candidate, "entry_price") or first_missing(
        "MarketData", market
    )
    if reason:
        return ComponentScore(name, 0.0, reason)
    minutes = settings.opening_range_minutes
    end = (datetime.combine(datetime.min, OPEN) + timedelta(minutes=minutes)).time()
    window = bars_in_window(market.today_bars, OPEN, end, settings.timezone)
    if len(window) != minutes or not complete(window, "high"):
        return ComponentScore(name, 0.0, f"missing: MarketData.today_bars needs the first {minutes} bars")
    range_high = max(bar.high for bar in window)
    broke_out = candidate.entry_price > range_high
    return ComponentScore(
        name, 1.0 if broke_out else 0.0, f"entry {candidate.entry_price} against opening range high {range_high}"
    )


def relative_volume(candidate: Candidate | None, market: MarketData | None, settings) -> ComponentScore:
    name = "relative_volume"
    reason = first_missing("Candidate", candidate, "timestamp") or first_missing("MarketData", market)
    if reason:
        return ComponentScore(name, 0.0, reason)
    if not market.today_bars:
        return ComponentScore(name, 0.0, "missing: MarketData.today_bars")
    sessions = recent_sessions(market, candidate, settings)
    if not sessions:
        return ComponentScore(
            name, 0.0, f"missing: MarketData.history_bars needs {settings.history_sessions} sessions"
        )
    until = local(candidate.timestamp, settings.timezone).time()
    today = volume_until(market.today_bars, until, settings.timezone)
    average = sum(volume_until(s, until, settings.timezone) for s in sessions) / len(sessions)
    if average <= 0:
        return ComponentScore(name, 0.0, "history has no volume in the window")
    rvol = today / average
    return ComponentScore(name, clip(rvol / 2), f"relative volume {rvol:.2f}")


def first_half_hour(bars, settings) -> tuple[Bar, ...]:
    return bars_in_window(bars, OPEN, FIRST_HALF_HOUR_END, settings.timezone)


def _half_hour_return(bars) -> float | None:
    if not complete(bars, "open", "close") or bars[0].open <= 0:
        return None
    return bars[-1].close / bars[0].open - 1


def intraday_momentum(candidate: Candidate | None, market: MarketData | None, settings) -> ComponentScore:
    name = "intraday_momentum"
    reason = first_missing("Candidate", candidate, "timestamp") or first_missing("MarketData", market)
    if reason:
        return ComponentScore(name, 0.0, reason)
    today = _half_hour_return(first_half_hour(market.today_bars, settings))
    if today is None:
        return ComponentScore(name, 0.0, "missing: MarketData.today_bars needs the first half hour")
    sessions = recent_sessions(market, candidate, settings)
    past = [_half_hour_return(first_half_hour(s, settings)) for s in sessions]
    if not sessions or any(r is None for r in past):
        return ComponentScore(
            name, 0.0, f"missing: MarketData.history_bars needs {settings.history_sessions} sessions"
        )
    sigma = pstdev(past)
    if sigma == 0:
        value = 1.0 if today > 0 else 0.0 if today < 0 else 0.5
    else:
        value = clip(0.5 + today / (2 * sigma))
    return ComponentScore(name, value, f"first half hour {today:+.3%} against typical {sigma:.3%}")


def _half_hour_range_and_volume(bars) -> tuple[float, float] | None:
    if not complete(bars, "open", "high", "low", "volume") or bars[0].open <= 0:
        return None
    price_range = (max(b.high for b in bars) - min(b.low for b in bars)) / bars[0].open
    return price_range, sum(b.volume for b in bars)


def volatility_and_volume_conditions(
    candidate: Candidate | None, market: MarketData | None, settings
) -> ComponentScore:
    name = "volatility_and_volume_conditions"
    reason = first_missing("Candidate", candidate, "timestamp") or first_missing("MarketData", market)
    if reason:
        return ComponentScore(name, 0.0, reason)
    today = _half_hour_range_and_volume(first_half_hour(market.today_bars, settings))
    if today is None:
        return ComponentScore(name, 0.0, "missing: MarketData.today_bars needs the first half hour")
    sessions = recent_sessions(market, candidate, settings)
    past = [_half_hour_range_and_volume(first_half_hour(s, settings)) for s in sessions]
    if not sessions or any(p is None for p in past):
        return ComponentScore(
            name, 0.0, f"missing: MarketData.history_bars needs {settings.history_sessions} sessions"
        )
    mean_range = sum(p[0] for p in past) / len(past)
    mean_volume = sum(p[1] for p in past) / len(past)
    if mean_range <= 0 or mean_volume <= 0:
        return ComponentScore(name, 0.0, "history has no range or no volume in the first half hour")
    range_part = clip(today[0] / mean_range / 2)
    volume_part = clip(today[1] / mean_volume / 2)
    return ComponentScore(
        name,
        (range_part + volume_part) / 2,
        f"range {today[0] / mean_range:.2f}x and volume {today[1] / mean_volume:.2f}x the average",
    )


@dataclass(frozen=True)
class SignalScore:
    components: tuple[ComponentScore, ...]
    value: float
    threshold: float
    passed: bool


def components(candidate, market, settings) -> tuple[ComponentScore, ...]:
    return (
        trend_direction(market, settings),
        intraday_momentum(candidate, market, settings),
        volatility_and_volume_conditions(candidate, market, settings),
        opening_range_breakout(candidate, market, settings),
        relative_volume(candidate, market, settings),
    )


def signal_score(scored: tuple[ComponentScore, ...], settings) -> SignalScore:
    value = sum(c.value for c in scored) / len(scored)
    threshold = settings.score_threshold
    return SignalScore(scored, value, threshold, value >= threshold)
