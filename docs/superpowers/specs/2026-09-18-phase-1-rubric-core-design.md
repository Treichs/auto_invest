# Phase 1 design: the rubric core

Date: 2026-09-18. Status: approved for planning. Source of truth for what it does not cover: [the blueprint](../../blueprint.md) revision 2.2 and [the build plan](../../build-plan.md) version 1.3. Nothing here reopens a locked decision.

## Part A. The whole system on one page

An autonomous system that trades US index ETFs, starting with SPY and QQQ, through Interactive Brokers Canada in a taxable cash account holding US dollars. Every candidate trade passes a two-tier rubric: eight must-pass checks, any one of which vetoes the trade, then a five-component signal score that must clear a threshold. Trades are sized from 0.5% risk per trade and the stop distance, inside a 25% per-symbol cap and an 80% total cap, with no borrowed money, at most 3 entries a day, and settled cash only. A 1% daily loss halts trading. Entries happen between 10:00 and 15:30 Eastern and everything is closed by 15:50. Limit orders only; a protective stop rests at the broker the moment an entry fills.

The rubric is plain Python that knows nothing about any trading engine. That is the ports and adapters pattern: the rubric defines simple input records (the port) and each engine gets a thin adapter that fills them and acts on the verdict. Research and backtests run on LEAN through QuantConnect's free plan, where the rubric files are pasted into the web editor. Paper and live trading run on self-hosted NautilusTrader in Docker on a small cloud server, whose risk engine enforces order caps and rate limits outside the strategy. Hard ceilings live in a file the strategy cannot change; operating settings may be tightened freely and loosened only through the stage gates: research, backtest with real costs, out-of-sample checks, port and confirm on the second engine, paper trading, live small, scale up.

Around the engine sits an operations layer, built in Phase 5: one Postgres database hosted on Supabase that the engine writes to and every screen reads from, a Grafana status board (view only, private), Telegram alerts through Apprise, a Healthchecks.io heartbeat, a daily reconciliation against the broker's own statement, a startup guard that refuses to run if trading mode and broker connection disagree, and a documented emergency stop. A React control panel comes after the paper gate. No language model sits in the order path: Claude Code builds the system and reviews the journal after the close.

Phase 1 delivers the rubric only: the decision record, the eight checks, the five score components, position sizing, the cost model, a settlement ledger, and the input records. No adapter, engine, database, or alert is built in this phase.

## Part B. Phase 1 specification

Every requirement below has an identifier so a test can name it. "Fails" means the check returns a result with `passed = False` and a reason naming the cause; a check never raises on bad input. "Missing" means the input object, or the named field on it, is `None` or empty.

### B1. Shape

- **R1.1** The rubric is a Python package inside `auto_invest`. It imports only the standard library and its own modules. A test scans every module in the package and fails if any imports `nautilus_trader`, `AlgorithmImports`, `QuantConnect`, `pandas`, or `numpy`.
- **R1.2** Every input record is a frozen dataclass. Every rubric function is a plain function that takes records plus a `Settings` object and returns a record. No function reads a file, the clock, or the network.
- **R1.3** The package exposes `RUBRIC_VERSION`, a string, stamped on every decision record.
- **R1.4** Phase 1 is long only. A candidate has no side field; every entry is a buy and every stop is below the entry. Reason: a cash account cannot sell short.
- **R1.5** All timestamps are timezone-aware. Time-of-day rules use the timezone named in settings (`America/New_York`).

### B2. Input records, the port

| Record | Fields | Who fills it later |
|---|---|---|
| `Quote` | symbol, bid, ask, timestamp | Engine data feed |
| `Bar` | symbol, start (timestamp), open, high, low, close, volume | Engine data feed; minute bars for today and the past 20 sessions, daily bars for the past 13 months |
| `InstrumentStatus` | symbol, listed_in_us (bool), halted (bool) | Engine instrument data |
| `Position` | symbol, quantity, average_price, stop_price | Engine portfolio |
| `AccountState` | start_of_day_equity, settled_cash (broker figure, may be None), positions (tuple of `Position`), entries_today, realised_pnl_today, unrealised_pnl_today, broker_connected, positions_reconciled, timestamp | Engine account and reconciliation |
| `Sale` | trade_date, proceeds | Adapter, from fills |
| `SettlementLedger` | start_of_day_settled_cash, buys_today, sales (tuple of `Sale`) | Adapter, carried across days |
| `Candidate` | symbol, entry_price, stop_price, timestamp | The strategy, when it spots an entry |
| `MarketData` | quote, today_bars (tuple of minute `Bar`), history_bars (tuple of minute `Bar` for prior sessions), daily_bars (tuple of daily `Bar`) | Adapter, bundling the feed |

- **R2.1** Any field may be `None`; the rubric treats `None`, and an empty tuple of bars, as missing. `AccountState.settled_cash` and `Position.stop_price` default to `None`; every other field must be given explicitly so an adapter cannot forget one silently.
- **R2.2** Records compare by value and are hashable, so a decision record can be serialised and compared in tests.

### B3. Settlement ledger

- **R3.1** `usable_settled_cash(ledger, on_date)` returns `start_of_day_settled_cash − buys_today + Σ proceeds` of every sale whose settlement date is on or before `on_date`, where settlement date is the next weekday after `trade_date`.
- **R3.2** A sale on Friday settles Monday: its proceeds are unusable on Friday, Saturday, and Sunday and usable from Monday. A sale on Monday settles Tuesday.
- **R3.3** Market holidays are not modelled in Phase 1. This is safe because a holiday is a day with no entries, so the only dates the ledger gets wrong are dates on which nothing can be bought. Recorded here so Phase 2 can add a calendar if the backtest needs one.
- **R3.4** The rubric's usable figure is `min(usable_settled_cash(ledger), account.settled_cash)` when the broker figure is present, else the ledger figure alone. A missing ledger fails the risk budget check.

### B4. Cost model

- **R4.1** `commission_per_side(shares, price)` = `0.0035 × shares`, raised to at least `0.35`, capped at `0.01 × shares × price`. Zero shares costs zero.
- **R4.2** `round_trip_commission(shares, price)` = twice R4.1.
- **R4.3** `spread_cost_round_trip(shares, quote)` = `shares × (ask − bid)`, which is half the spread paid on entry and half on exit.
- **R4.4** `total_cost_round_trip` = R4.2 + R4.3.
- **R4.5** Exchange, clearing, and regulatory pass-through fees are excluded in Phase 1. Recorded so Phase 2's brokerage model can be compared against this figure.
- **R4.6** Worked example: 2 shares at 625.00 with a one-cent spread costs 0.70 commission and 0.02 spread, 0.72 in total.

### B5. Position sizing

- **R5.1** Inputs: `Candidate`, `AccountState`, usable settled cash (R3.4), `Settings`. Output `Size` with `budget`, `shares`, `risk_at_budget`, `risk_at_shares`.
- **R5.2** `stop_fraction = (entry − stop) / entry`. If stop is missing, not below entry, or entry is not positive, the result is a `Size` with zero shares and a reason.
- **R5.3** `budget` is the smallest of: `risk_per_trade × equity / stop_fraction`; `per_symbol_cap × equity`; `total_exposure_cap × equity − current exposure` (sum of `quantity × average_price` over open positions); usable settled cash. Never below zero.
- **R5.4** `shares = floor(budget / entry)`. Whole shares only, because the Interactive Brokers API does not accept fractional or cash-quantity stock orders.
- **R5.5** `risk_at_budget = budget × stop_fraction`; `risk_at_shares = shares × (entry − stop)`.
- **R5.6** Acceptance test, the blueprint's $5,000 table. Equity 5,000, no positions, usable settled cash 5,000, entry 100.00. Stop 99.60 (0.4% away): budget 1,250.00, risk at budget 5.00. Stop 98.00 (2% away): budget 1,250.00, risk at budget 25.00. Both to the cent. With entry 650.00 and the same stops, shares is 1 and the budget is unchanged.
- **R5.7** Budget is reduced by settled cash: equity 5,000 with usable settled cash 900 gives budget 900.

### B6. The eight must-pass checks

Each check is a function returning `CheckResult(name, passed, reason)`. Names are the blueprint's, in snake case. Missing data fails with reason `missing: <record>.<field>`.

| # | Name | Passes when | Fails when missing |
|---|---|---|---|
| 1 | `data_is_sane` | Quote age (`candidate.timestamp − quote.timestamp`) ≤ `quote_max_age_seconds`; bid > 0 and ask ≥ bid; quote mid within ± `price_band` of the last daily close | quote, any quote field, daily bars |
| 2 | `instrument_is_eligible` | `listed_in_us` and not `halted` and symbol in `approved_symbols` | instrument status |
| 3 | `market_is_liquid` | `(ask − bid) / mid ≤ spread_cap` and today's volume so far ≥ `volume_floor` | quote, today's bars |
| 4 | `trade_beats_its_costs` | `total_cost_round_trip ≤ max_cost_fraction_of_risk × risk_at_shares` and `risk_at_shares > 0` | size, quote |
| 5 | `exit_is_defined` | `0 < stop_price < entry_price` | candidate stop |
| 6 | `risk_budget_has_room` | order value (`shares × entry`) ≤ `order_value_cap × equity`; ≤ `per_symbol_cap × equity`; exposure + order value ≤ `total_exposure_cap × equity`; `entries_today < entries_per_day`; order value ≤ usable settled cash; shares ≥ 1 | account, ledger, size |
| 7 | `daily_loss_limit_not_hit` | `realised + unrealised > −daily_loss_limit × equity` (a loss exactly at the limit fails) | either P&L field, equity |
| 8 | `system_is_healthy` | `broker_connected`, `positions_reconciled`, no open position in the symbol, candidate time inside `[entry_window_start, entry_window_end)` Eastern | any of the four |

- **R6.1** Each check has a passing test, a failing test for each clause, and a missing-data test for each input it reads.
- **R6.2** Check 8 records which clause failed, so the journal can count "outside window" separately from "already holding".
- **R6.3** The worked cost example: risk at shares 5.00 with cost 0.72 is 14.4% and fails at the 10% placeholder; risk 25.00 is 2.9% and passes.

### B7. The five signal score components

Each is a function returning a float in `[0, 1]`. Missing or insufficient data returns `0.0` with a reason, never an exception. "Session" means one trading day's minute bars. "First half hour" means bars starting from 09:30 up to and including 09:59 Eastern. History means the 20 most recent complete sessions before today.

| Component | Formula |
|---|---|
| `trend_direction` | From daily closes: for lookbacks of 21, 63, 126, and 252 trading days, return = `close[−1] / close[−1 − L] − 1`. Score = number of positive returns ÷ 4. Needs 253 closes |
| `intraday_momentum` | `r` = today's first-half-hour return (`last close / first open − 1`). `σ` = population standard deviation of the same return across the 20 history sessions. Score = `clip(0.5 + r / (2σ), 0, 1)`. If `σ = 0`: 1 when `r > 0`, 0 when `r < 0`, 0.5 when `r = 0` |
| `volatility_and_volume_conditions` | Range = `(max high − min low) / first open` over the first half hour; volume = sum over the first half hour. Score = mean of `clip(range_today / mean_range_history / 2, 0, 1)` and `clip(volume_today / mean_volume_history / 2, 0, 1)`. Twice the average scores 1 |
| `opening_range_breakout` | Opening range high = max high of bars starting 09:30 to 09:30 + `opening_range_minutes` exclusive. Score = 1 if `entry_price > opening range high`, else 0 |
| `relative_volume` | Today's volume up to the candidate time ÷ mean over history sessions of volume up to the same time of day. Score = `clip(rvol / 2, 0, 1)` |

- **R7.1** `signal_score(components)` = arithmetic mean of the five. `SignalScore` records each component, the mean, the threshold used, and `passed = mean ≥ score_threshold`.
- **R7.2** Each component has tests for: a clear positive case scoring 1, a clear negative case scoring 0, a midpoint, and missing data scoring 0 with a reason.
- **R7.3** The formulas are placeholders. They exist so Phase 1 is testable and so Phase 2 has a baseline to vary. Changing a formula, weight, or the threshold is a loosening and goes through the stage gates.

### B8. Decision record

- **R8.1** `DecisionRecord` fields: `rubric_version`, `symbol`, `timestamp`, `checks` (tuple of eight `CheckResult` in blueprint order), `score` (`SignalScore` or None), `size` (`Size` or None), `verdict` (`"accepted"` or `"rejected"`), `rejected_by` (a check name, `"signal_score"`, `"position_size"`, or None).
- **R8.2** `decide(candidate, market_data, instrument_status, account, ledger, settings)` runs the whole rubric and returns a `DecisionRecord`. It computes size first, because checks 4 and 6 need it, then runs all eight checks, then the score. All eight checks are always evaluated and recorded, even after one fails.
- **R8.3** Verdict is `accepted` only when all eight checks pass, the score passes, and `shares ≥ 1`. `rejected_by` is the first failing check in blueprint order, else `signal_score`, else `position_size`.
- **R8.4** `to_dict()` returns plain Python types (str, float, int, bool, None, lists, dicts) so the journal bridge can store it without knowing the record classes. A test round-trips a record through `json.dumps`.
- **R8.5** A reader can tell from the record alone why a trade was accepted or rejected: every `CheckResult.reason` is a sentence naming the value and the limit.

### B9. Settings added in Phase 1

These join `config/settings.toml` and `config/ceilings.toml`, each with the comment `unvalidated placeholder, Phase 2 sets the real value`. The loader's ceiling check gains the direction column.

| Setting | Value | Ceiling direction |
|---|---|---|
| `quote_max_age_seconds` | 5 | at most |
| `price_band` | 0.10 | at most |
| `spread_cap` | 0.0005 | at most |
| `volume_floor` | 1000000 | at least |
| `max_cost_fraction_of_risk` | 0.10 | at most |
| `score_threshold` | 0.6 | at least |
| `order_value_cap` | 0.25 | at most |
| `opening_range_minutes` | 5 | not ceilinged |
| `history_sessions` | 20 | not ceilinged |

- **R9.1** Loading fails with a message naming the setting if any ceilinged value is on the wrong side of its ceiling.

### B10. Out of scope for Phase 1

Engine adapters, order placement, the resting stop, reconciliation, the database bridge, alerts, the halted trading state, a holiday calendar, exchange pass-through fees, short selling, and any change to the ceilings file.

### B11. Acceptance, the whole phase

1. `uv run pytest` passes with every requirement above covered by at least one test that names it.
2. R1.1's import scan passes.
3. R5.6 matches the blueprint's table to the cent.
4. Every check and every score component has a missing-data test.
5. A rejected `DecisionRecord`, printed as a dictionary, states which check failed and why in plain words.
