# Phase 2 design: the LEAN adapter

Date: 2026-09-18. Status: approved for planning. Source of truth for what it does not cover: [the blueprint](../../blueprint.md) revision 2.2, [the build plan](../../build-plan.md) version 1.3, and [the Phase 1 design](2026-09-18-phase-1-rubric-core-design.md). Nothing here reopens a locked decision, and nothing here changes the rubric.

## Part A. What Phase 2 delivers and the decisions it rests on

Phase 2 puts the Phase 1 rubric inside a LEAN algorithm on QuantConnect's free plan and runs a baseline backtest on SPY and QQQ at minute resolution with Interactive Brokers costs. The adapter is the thin wrapper the blueprint budgets for: it fills the rubric's input records from LEAN data, calls `decide()`, and turns an accepted verdict into orders. Every rule lives in the rubric; the adapter feeds it honest state and never re-checks a rule.

Decisions taken before this spec, in the order they were made:

| Decision | Choice | Rejected |
|---|---|---|
| Hold-out ([ADR 0017](../../adr/0017-hold-out-period-from-2025.md)) | 2025-01-01 onward, open-ended | Rolling two years; from 2024 |
| In-sample | 2019-01-01 to 2024-12-31, one calendar year per backtest | 2016 start (more runs to log); 2022 start (one bear market only) |
| Candidate | Every 5 minutes while flat inside the window: entry at the ask, stop at the opening-range low | Breakout-only trigger (makes the breakout component constant); ATR stop (a new tunable) |
| Fees | Custom LEAN fee model calling `rubric.costs.commission_per_side`, IB Tiered | LEAN's built-in IB model, which is Fixed pricing at $0.005 a share with a $1.00 minimum |
| Exits | Stop-market for the protective stop; limit at the bid, re-priced each minute, for the forced close | Stop-limit (can be skipped in a gap); market order at the close (breaks limit-orders-only) |
| Layout | `src/auto_invest/adapters/lean/` mirrors the web project | Top-level `quantconnect/` folder |

Facts from QuantConnect's current documentation that shaped the design: the free plan allows 10 KB of log per backtest, 10,000 orders per backtest, 25 files per project of 32 KB each, subfolders, and `pydantic` 2.12. LEAN's Interactive Brokers brokerage model on a cash account settles US equities T+1 at 06:00 skipping weekends and market holidays, applies no slippage, and fills a limit buy at `min(open, limit)` once a bar's low crosses the limit.

## Part B. Phase 2 specification

Every requirement has an identifier so a test or a runbook step can name it. "Aware" means a `datetime` with `tzinfo` set to America/New_York.

### B1. The adapter contract

This section is the port. It states, for every rubric input, where the value comes from in LEAN and which rubric assumption it honours. The rubric assumes: bars are chronological, `daily_bars[-1]` is the previous session's close, no tuple holds a `None` element, every minute bar carries a volume, `SettlementLedger.sales` holds only sales not already inside `start_of_day_settled_cash`, `InstrumentStatus` is for the candidate's own symbol, and every timestamp is aware.

- **R1.1 Time.** LEAN hands the algorithm naive New York datetimes. The adapter attaches America/New_York to every one before it reaches the rubric: `self.time`, bar `time`, quote bar `end_time`.
- **R1.2 Minute bars.** A LEAN `TradeBar` becomes `Bar(symbol, start=aware(time), open, high, low, close, volume)`. LEAN trade bars always carry a volume. A fill-forward bar (LEAN's placeholder for a minute with no trade) is never stored.
- **R1.3 Quote.** The latest minute `QuoteBar` becomes `Quote(symbol, bid.close, ask.close, aware(end_time))`. When the slice has no quote bar for the symbol, the adapter passes `Quote(symbol, None, None, None)` and the rubric fails closed.
- **R1.4 `today_bars`.** Every real minute bar of the current session so far, in arrival order. LEAN delivers a bar when it closes, so the bar ending at the candidate time is complete, not in progress.
- **R1.5 `history_bars`.** The minute bars of the `history_sessions` sessions before today, oldest first. At the first bar of a new session the adapter moves yesterday's bars into history and drops the oldest session beyond the cap. LEAN warm-up of 35 calendar days at minute resolution fills the store before the first in-sample session; no orders are placed while `is_warming_up`.
- **R1.6 `daily_bars`.** At the first bar of each session the adapter requests 253 daily `TradeBar` objects. With LEAN's `daily_precise_end_time` (default `True`) daily bars end at 16:00, so a request made during the session returns bars through yesterday. The adapter asserts the last bar's date is before today and drops it if not.
- **R1.7 `InstrumentStatus`.** Built for the candidate's own symbol. `listed_in_us` is true when the security's market is USA. `halted` is true when this minute's trade bar is absent or fill-forward; LEAN has no halt feed, so a missing print is the honest fail-closed signal.
- **R1.8 `Position`.** One per invested holding: LEAN quantity and average price, plus the stop price the adapter placed for that symbol, or `None` if no stop is resting.
- **R1.9 `AccountState`.** `start_of_day_equity` = total portfolio value at the session's first bar. `settled_cash` = LEAN's settled cash (`portfolio.cash`; unsettled sale proceeds sit in a separate book). `entries_today` = entry fills counted by the adapter since the session start. `realised_pnl_today` = LEAN's total net profit now minus its value at the session start. `unrealised_pnl_today` = LEAN's total unrealised profit. `broker_connected` and `positions_reconciled` are `True`: in a backtest LEAN is the broker, so there is nothing to reconcile against; Phase 4 fills them from NautilusTrader. `timestamp` = aware `self.time`.
- **R1.10 `SettlementLedger`.** `start_of_day_settled_cash` = settled cash at the session's first bar. LEAN settles at 06:00 on the next market day, so yesterday's sales are already inside that figure. `buys_today` = sum over today's buy fills of fill value plus fee. `sales` = one `Sale(today, fill value minus fee)` per sell fill today, and nothing older. The rubric's own ledger dates a sale's settlement to the next weekday, so a sale today is never counted today, matching LEAN.
- **R1.11 `Candidate`.** Proposed when all of: the entry window is open, the minute is a multiple of `candidate_interval_minutes`, the symbol has no holding and no open entry order. `entry_price` = the ask from R1.3. `stop_price` = the lowest low of the bars starting from 09:30 for `opening_range_minutes` minutes, or `None` if those bars are not all present. Nothing is filtered: a stop at or above the entry reaches the rubric and is logged as its rejection.
- **R1.12 Nothing missing.** The rubric needs nothing LEAN cannot supply. The rubric package is not edited in this phase; if a future change seems to need it, stop and report.

### B2. Files and layout

- **R2.1** The web project mirrors into `src/auto_invest/adapters/lean/`: `main.py` (the `QCAlgorithm` subclass and the fee model; imports LEAN) and `lean_adapter.py` (plain Python, no LEAN import: conversions, session store, day ledger, opening-range stop, log lines, rubric hash).
- **R2.2** Both files import the rubric as `rubric.…`, the name it has in the web project. `[tool.pytest.ini_options] pythonpath` gains `src/auto_invest` and `src/auto_invest/adapters/lean` so the same imports resolve locally.
- **R2.3** `scripts/build_quantconnect_project.py`, run as `uv run python scripts/build_quantconnect_project.py`, writes the paste-ready tree to `build/quantconnect/` (git-ignored): `main.py`, `lean_adapter.py`, `settings.py` (copied unchanged from `src/auto_invest/settings.py`), `settings_snapshot.py` (generated, R7.3), and `rubric/` (every `.py` copied byte for byte). It prints the file count and the rubric hash (R7.1).
- **R2.4** The tree is 13 files, each under 32 KB. A test fails if any file in the tree exceeds 32 KB or the count exceeds 25.
- **R2.5** `main.py` holds four constants: `IN_SAMPLE_YEAR`, `HOLD_OUT_START = date(2025, 1, 1)` with a comment citing ADR 0017, `STARTING_CASH = 5000`, and `SYMBOLS`, taken from `settings.approved_symbols` at start-up rather than repeated.

### B3. The trading day

- **R3.1** `initialize` sets the start and end dates to `IN_SAMPLE_YEAR`, raises with a message naming ADR 0017 if the end date is on or after `HOLD_OUT_START`, sets cash, sets `BrokerageName.INTERACTIVE_BROKERS_BROKERAGE` with `AccountType.CASH`, adds each symbol at minute resolution with the Tiered fee model (R5.1), sets warm-up, builds `Settings` (R7.3), logs the rubric hash and version and the Object Store quota, and registers the three scheduled events below.
- **R3.2** Session start is detected in `on_data` by a date change. The adapter then: snapshots equity, settled cash, and net profit; resets `entries_today`, `buys_today`, and `sales`; rolls bars per R1.5; fetches daily bars per R1.6.
- **R3.3** `schedule.on(date_rules.every_day(SPY), time_rules.at(entry_window_start))` opens the window; `time_rules.at(entry_window_end)` closes it and cancels open entry orders; `time_rules.at(forced_close)` starts the forced close (R4.4). All three times come from settings.
- **R3.4** Candidate ticks run inside `on_data`, not a scheduled event, so the minute's bars and quotes are in hand when the rubric is called. For each symbol meeting R1.11 the adapter builds the records, calls `decide()`, logs the record (B6), and on `accepted` places the entry (R4.1).

### B4. Orders

- **R4.1 Entry.** `limit_order(symbol, size.shares, candidate.entry_price)`. One open entry order per symbol at most. If it is still open at the next candidate tick it is cancelled; the tick may then propose a fresh candidate.
- **R4.2 Stop.** On the entry's fill event: `entries_today += 1`, `buys_today` updated, `stop_market_order(symbol, -filled_quantity, candidate.stop_price)` placed, and the stop price recorded for R1.8.
- **R4.3 Stop fill.** On the stop's fill event: a `Sale` recorded per R1.10 and the stop cleared.
- **R4.4 Forced close.** At `forced_close`: cancel every resting stop and open entry order, then for each holding place a limit sell at the current bid for the full quantity. Each following minute, while any close order is open, `update_limit_price` to the new bid. On fill: a `Sale` recorded. No market order is ever sent.
- **R4.5 Fills are whole.** LEAN's equity fill model fills SPY and QQQ orders in full; partial fills are not handled.
- **R4.6 Order budget.** Worst case per day per symbol is one cancelled entry per tick plus three entries, three stops, and one close, well under 10,000 a year. `on_end_of_algorithm` logs the order count so the budget is visible.

### B5. Fees, fills, settlement

- **R5.1 Fees.** A `FeeModel` subclass in `main.py` returns `OrderFee(CashAmount(commission_per_side(abs(quantity), fill_price), "USD"))` using `rubric.costs`. Exchange and regulatory pass-through fees stay excluded, as Phase 1 recorded (R4.5 there).
- **R5.2 Spread.** The entry is a limit at the ask, so the half-spread is paid on entry; the forced close is a limit at the bid, so it is paid on exit. No slippage model is added; LEAN's IB model applies none.
- **R5.3 Settlement.** LEAN's cash-account settlement model holds sale proceeds unsettled until 06:00 on the next market day and its buying-power model rejects an order that exceeds settled cash. That engine-side guard sits outside the rubric, matching the blueprint's "limits sit outside the strategy". The rubric's settled-cash check runs first and is what the log records.

### B6. Decision log

- **R6.1 One line per decision.** Every call to `decide()` appends one JSON line: `timestamp`, `symbol`, `verdict`, `rejected_by`, `reason` (the failing check's reason, else the score's), the eight check names each mapped to `true`/`false`, `score`, `shares`, and `rubric_version`. Accepted decisions carry the full `to_dict()` under `record`.
- **R6.2 Storage.** Lines are held in memory and saved in `on_end_of_algorithm` to the Object Store as `auto_invest/<algorithm_id>/decisions.jsonl`. The log gets the key, the line count, and one line of rejection counts per check.
- **R6.3 Size.** About 33,000 lines a year at roughly 300 bytes, about 10 MB per backtest. `initialize` logs `object_store.max_size` so the quota is known on the first run.
- **R6.4 Counting.** `lean_adapter.rejection_counts(lines)` returns a dict of `rejected_by` → count; the runbook shows how to run it on a downloaded file.

### B7. Identity check and settings snapshot

- **R7.1 Rubric hash.** `lean_adapter.rubric_hash(folder)` reads every `.py` in the folder in sorted name order, replaces CRLF with LF, and returns the SHA-256 of the concatenation. The build script prints it for `src/auto_invest/rubric/`; `initialize` logs it for the pasted `rubric/` folder. Equal hashes mean identical files; the runbook compares the first eight characters and the research log records them.
- **R7.2 Adapter identity.** The build script also prints the git commit so the research log can name which `main.py` and `lean_adapter.py` were pasted.
- **R7.3 Settings snapshot.** The build script generates `settings_snapshot.py` containing `SETTINGS` and `CEILINGS`, the two TOML files parsed into dictionaries. `main.py` builds `Settings.model_validate(SETTINGS)` and `Ceilings.model_validate(CEILINGS)` and calls `check_against_ceilings`, so a backtest cannot start on a setting outside its ceiling. `settings.py` is pasted unchanged.
- **R7.4 Never edit the tree.** `build/quantconnect/` is output only. Changes are made in the repo and rebuilt, so the pasted files can never drift from Git.

### B8. Settings added in Phase 2

| Setting | Value | Ceiling |
|---|---|---|
| `candidate_interval_minutes` | 5 | Not ceilinged; it is a cadence, not a limit |

Added to `Settings` in `settings.py` and to `config/settings.toml`. The ceilings file is not touched.

### B9. Tests

All in `tests/`, run by `uv run pytest`, no LEAN installed. Inputs are small duck-typed fakes with the LEAN attribute names.

- **R9.1** Bar and quote conversion: aware timestamps, field mapping, missing quote bar → `None` fields.
- **R9.2** Session store: bars stay chronological; a date change rolls today into history; history never exceeds `history_sessions`; fill-forward bars are dropped and mark the symbol halted.
- **R9.3** Daily bars: a last bar dated today is dropped; 253 remain otherwise.
- **R9.4** Day ledger: `entries_today` counts fills not orders; `buys_today` includes fees; `sales` holds only today's, net of fees; reset at session start.
- **R9.5** Opening-range stop: lowest low of the first `opening_range_minutes` bars; `None` when a bar is missing.
- **R9.6** Log line: round-trips through `json.loads`; `rejection_counts` on a rejected, an accepted, and a score-rejected line.
- **R9.7** Rubric hash: same folder same hash; one changed byte changes it; CRLF and LF copies match.
- **R9.8** Build script: produces exactly the 13 files, each under 32 KB, `rubric/` byte-identical to the source, `settings_snapshot.py` importable with dictionaries equal to the TOMLs.
- **R9.9** `lean_adapter.py` imports no LEAN, `pandas`, or `numpy`, checked the same way as the rubric's import guard.
- **R9.10** `main.py` is not unit-tested; its check is the first cloud backtest (B12).

### B10. Docs

- **R10.1** `docs/research-log.md`: one table, one row per run: date, in-sample year, what changed, rubric hash (8 characters), trades, net return after costs, max drawdown, top rejecting check and its count. A first row is filled by the baseline run. Phase 3 counts the rows.
- **R10.2** `docs/runbooks/quantconnect-baseline-backtest.md`: the first runbook and the template for Phase 5's. Numbered literal steps, each with the exact label to click or value to type, one line on why, and what success looks like: build the tree; create the project; add `rubric/` as a folder with its `__init__.py`; paste each file; set `IN_SAMPLE_YEAR`; run; compare the hash; read the counts; download the decisions file from the Object Store page and the orders list from the backtest page; fill the research-log row. Anything hard to undo is flagged before the step.
- **R10.3** The build plan's Phase 2 checklist is ticked as items land.

### B11. Out of scope

Any edit to the rubric package or to `config/ceilings.toml`; tuning any setting; any run touching 2025 or later; walk-forward, Deflated Sharpe, or Probability of Backtest Overfitting; a market-holiday calendar; partial fills; short selling; NautilusTrader; the database, alerts, or dashboard.

### B12. Acceptance

1. `uv run pytest` passes with every R9 requirement covered by a test that names it, and the Phase 1 suite untouched.
2. `uv run python scripts/build_quantconnect_project.py` writes 13 files and prints a hash that matches the one the cloud run logs.
3. A baseline backtest of one in-sample year completes on the free plan with Tiered fees and the entry at the ask, and its log shows the hash, the rejection counts, and the Object Store key.
4. In that run every position had a stop and none was held after 15:50; the order count is under 10,000.
5. The research log has its first row, and no run has an end date in 2025 or later.
