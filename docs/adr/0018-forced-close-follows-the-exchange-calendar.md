# 0018. Forced close follows the exchange calendar

**Status**: Accepted
**Date**: 2026-09-19

## Context
The 2020 backtest held a QQQ position over the weekend of 2020-11-27 with no stop. That day was a half day (market closed 13:00), and the forced close was scheduled with `time_rules.at(forced_close)`, a fixed 15:50 clock time as spec R3.3 states. It fired after the close, cancelled the protective stop, and the close order could not fill until Monday's open. Spec B11 left a market-holiday calendar out of Phase 2; this is the consequence.

## Decision
The forced close is scheduled with LEAN's exchange-calendar-aware rule `time_rules.before_market_close(symbol, 10)`, so it fires ten minutes before the actual close: 15:50 on a normal day, 12:50 on a half day. The `forced_close` setting stays as the documented normal-day time; the entry window still opens and closes on `time_rules.at(...)`. This deviates from spec R3.3.

Rejected: refusing to open positions on early-close days. It avoids the overnight hold but throws away trading days, and LEAN already knows the calendar.

## Consequences
No position outlives its session and no stop is cancelled after the close, whatever the exchange calendar says. `forced_close` in settings no longer controls when the close fires in LEAN; it remains the documented time and the upper bound for the entry window in settings validation. The NautilusTrader adapter must find the equivalent calendar-aware trigger rather than a clock time. The 2020 run is re-run and recorded as a new research-log row.
