# Automated trading system build plan

Eight phases from an empty folder to small live trades, built with Claude Code at a few hours a week. Nothing costs money until the strategy has proved itself on paper data it has never seen.

Build plan, version 1.3. Written 18 September 2026. QuantConnect and Interactive Brokers accounts are open. Account type decided: cash account to start, so the entries cap is 3 a day. Companion to the final blueprint, revision 2.2. Engineering guidance only, not financial or tax advice.

## Timeline at a few hours a week

Estimates assume about three hours a week. Teal is build time. Amber is time the system must simply run while you watch.

- 0 Foundations: 2 weeks
- 1 Rubric core: 4 weeks
- 2 Research: 6 weeks
- 3 Go or no-go: 3 weeks
- 4 Port and confirm: 6 weeks
- 5 Operations layer: 5 weeks
- 6 Paper trading: 2 + 6 weeks
- 7 Live, small: 8 weeks or more

About eight months to the first real trade, and that is only if Phase 3 says go. Phases 0 to 3, about 15 weeks, cost $0. If the strategy fails the go or no-go gate, you stop there having spent nothing but time.

## Accounts to review before you start

Everything you will sign up for, in the order the plan needs it. **Already open: QuantConnect and Interactive Brokers.** The rest are free and take minutes.

| Account                                                                                         | Needed                                   | Cost                                           | What to review                                                                                                                                                                                                                                                                                                                         |
|-------------------------------------------------------------------------------------------------|------------------------------------------|------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [QuantConnect](https://www.quantconnect.com/pricing/)                                           | Done                                     | Free plan                                      | Free covers backtesting. No local tool and no API on free. Do not pay for anything                                                                                                                                                                                                                                                     |
| GitHub                                                                                          | Phase 0                                  | Free                                           | One new private repository                                                                                                                                                                                                                                                                                                             |
| Claude plan with Claude Code                                                                    | Phase 0                                  | Your existing plan                             | That its usage limits suit a few hours of Claude Code a week                                                                                                                                                                                                                                                                           |
| [Interactive Brokers Canada](https://www.interactivebrokers.ca/en/pricing/commissions-home.php) | Done. Remaining setup happens in Phase 4 | No minimum for a cash account, no platform fee | Cash or margin account, see below. Tiered commissions. [Real-time US data package](https://www.interactivebrokers.ca/en/pricing/market-data-pricing.php), its price, and any minimum balance. API access through IB Gateway for US-listed securities. Two-factor login. A second username for viewing. The paper account comes with it |
| [Supabase](https://supabase.com/pricing)                                                        | Phase 5                                  | Free plan                                      | 500 MB database, two projects, pauses after a quiet week, no backups. The plan handles the last two. Check you have a free project slot                                                                                                                                                                                                |
| Telegram                                                                                        | Phase 5                                  | Free                                           | A personal account, then a bot you create inside the app                                                                                                                                                                                                                                                                               |
| [Healthchecks.io](https://healthchecks.io/about)                                                | Phase 5                                  | Free plan                                      | 20 checks included. You need one or two                                                                                                                                                                                                                                                                                                |
| Cloud server provider                                                                           | Phase 6                                  | About $5 to $10 a month                      | One small Linux server, billed monthly, no contract. Providers not yet compared                                                                                                                                                                                                                                                        |
| Private network tool, optional                                                                  | Phase 6                                  | Usually free for personal use                  | Phase 6 compares this with a secure tunnel. Nothing to sign up for yet                                                                                                                                                                                                                                                                 |
| Databento, only if needed                                                                       | Phase 4                                  | Pay for what you use                           | Only if Interactive Brokers minute history does not reach far enough back                                                                                                                                                                                                                                                              |
| Kraken Pro                                                                                      | Crypto phase                             | Free to hold                                   | Fee schedule, and that it is still on the Canadian regulators' authorised list                                                                                                                                                                                                                                                         |
| Accountant                                                                                      | Before Phase 7                           | One consultation                               | Whether your gains will count as business income                                                                                                                                                                                                                                                                                       |

### With the Interactive Brokers account already open

The multi-day approval wait in Phase 4 is gone. You can set up two-factor login and find the paper account now if you like, since both are free. Hold off on two things until Phase 4: the real-time data subscription, because it bills monthly, and funding beyond what the account needs, because no real money trades until Phase 7.

### Decided: cash account to start, 3 entries a day

In a cash account you may buy and sell the same day, but only with settled money, and sale proceeds settle the next business day. Each dollar can be used once a day. With the 25% position cap, that allows three entries a day, so the entries cap is 3.

The rubric gets a settled-cash check, so it can never buy with unsettled money. Selling stock bought with unsettled funds can restrict an account for 90 days. Research and paper trading must run under the same rule: 3 entries, settled cash only. Otherwise the tests would describe a system you cannot run.

Later option: a margin account, USD 2,000 minimum, lets proceeds be reused the same day without any borrowing. Moving to it counts as loosening a limit, so it goes back through backtest and paper first.

## How each phase is laid out

Every phase uses the same template, so you always know where to look.

| Part               | What it tells you                                             |
|--------------------|---------------------------------------------------------------|
| Goal               | What exists at the end that did not exist before              |
| Time and cost      | Estimate at three hours a week, and any new monthly cost      |
| You do             | Things only you can do: accounts, approvals, decisions        |
| Checklist          | The work, in order. Tick boxes save in this browser           |
| Exit criteria      | All must be true before the next phase starts                 |
| Claude Code prompt | Ready to paste into Claude Code in VS Code to start the phase |

### Standing rules for every Claude Code session

Phase 0 writes these into the repo's CLAUDE.md file, which Claude Code reads at the start of every session.

- Plan first in plain language, then wait for approval before changing anything.
- Existing, maintained libraries before custom code. Names come from the blueprint, never invented.
- Every rubric function has tests. A check that cannot be evaluated fails.
- No loose comments in code. Tidy folders. No file or folder lists in documentation.
- Decisions are recorded as architecture decision records, one short file per decision.
- Never commit secrets. Credentials live in an environment file that Git ignores.
- Never set trading mode to live, never raise a hard ceiling, and never place an order outside the paper account. Those are yours alone.

## Phase 0: Foundations

- **Goal**: A clean repo that Claude Code understands
- **Time**: 2 weeks, about 5 hours
- **New cost**: $0

### You do

- [x] Create a free QuantConnect account. Done
- [x] Create a private GitHub repository. Done
- [ ] Install VS Code, Claude Code, Git, and Python 3.12 or newer
- [x] Save the blueprint into the repo as docs/blueprint.md, using the page's own text. Done

### Checklist

- [ ] Claude Code writes CLAUDE.md from the standing rules above
- [ ] Project skeleton with a Python package for the rubric, a tests folder, and a docs folder
- [ ] First architecture decision records, one per row of the blueprint's "Decisions, locked" table
- [ ] Git ignore file and an example environment file with no real values
- [ ] One settings file with every number from the blueprint: 0.5% risk, 1% daily loss, 25% and 80% caps, 3 entries a day, settled cash only, entry window, forced close
- [ ] A separate hard ceilings file the settings can never exceed
- [ ] Test runner set up, with one passing placeholder test

### Exit criteria

- Tests run with one command and pass.
- Settings load and are rejected if any value exceeds its hard ceiling.
- No secrets anywhere in Git history.

### Claude Code prompt, Phase 0

``` text
You are helping me start a personal automated trading system. The full design is in docs/blueprint.md. Read it fully first.

Show me a short plan in plain language and wait for my approval before changing anything.

Phase 0 goal: a clean, minimal Python project.
1. Write CLAUDE.md containing the standing rules from the build plan: plan first, existing libraries before custom code, names from the blueprint only, tests for every rubric function, fail closed, no loose comments, tidy folders, no file lists in docs, decisions as ADRs, never commit secrets, never set live mode, never raise a hard ceiling, never place orders outside paper.
2. Create the skeleton: a rubric package, tests, docs with an ADR folder. Use the ports and adapters pattern: the rubric package must not import any trading engine.
3. Write one ADR per row of the blueprint's "Decisions, locked" table. Keep each under 15 lines.
4. Create the settings file with every number from the blueprint and a separate hard ceilings file. Use pydantic to load both and reject any setting above its ceiling.
5. Set up pytest, a .gitignore, and an example environment file with placeholder values only.

I am not a tooling expert. Explain each setup step simply and tell me exactly what to type.
```

## Phase 1: Rubric core

- **Goal**: The rubric as plain, tested Python that knows nothing about any engine
- **Time**: 4 weeks, about 12 hours
- **New cost**: $0

### Checklist

- [x] Decision record object that stores every check result, the score, the rubric version, and the final verdict
- [x] All eight must-pass checks as plain functions, named as in the blueprint: data is sane, instrument is eligible, market is liquid, trade beats its costs, exit is defined, risk budget has room (order value, per-symbol cap, total exposure, entries today, settled cash), daily loss limit not hit, system is healthy (broker connected, positions match, not already holding, inside the entry window). The engine places the stop and reports the connection; the rubric only checks what it is told
- [x] Five score components, equal weight: trend direction, intraday momentum, volatility and volume conditions, opening range breakout, relative volume
- [x] Position size function: 0.5% risk and stop distance, clipped by the 25% and 80% caps, no leverage
- [x] Cost model: Interactive Brokers tiered commission with the USD 0.35 minimum and 1.0% cap, plus spread
- [x] Tests for every function, including missing data for every input
- [x] A test that reproduces the blueprint's $5,000 table: $1,250 position, $5 at risk with a 0.4% stop, $25 with a 2% stop

### Exit criteria

- All tests pass, and the rubric package imports no trading engine.
- Every check returns "fail" when its data is missing.
- The $5,000 worked example matches the blueprint to the dollar.
- You can read a decision record and understand why a trade was accepted or rejected.

### Claude Code prompt, Phase 1

``` text
Read CLAUDE.md and docs/blueprint.md first. Show me a short plan in plain language and wait for my approval before changing anything. Use existing libraries before writing custom code. Explain anything technical simply.

Phase 1 goal: build the trade rubric from the blueprint's "The trade rubric" section as plain Python with no trading engine imports.

Build, in this order, with tests written alongside each piece:
1. A decision record that captures every check result, the score, the rubric version, and the verdict.
2. The eight must-pass checks. Any check that cannot be evaluated must return fail.
3. The five signal score components at equal weight, each returning a value between 0 and 1, plus the combined score and threshold test.
4. The position size function: 0.5% risk, stop distance, clipped by the 25% per-symbol and 80% total caps, no leverage. This is a cash account, so model settled cash: sale proceeds become usable the next business day, and an order that needs unsettled cash must fail.
5. The cost model: IBKR tiered commission, USD 0.35 minimum, 1.0% of trade value cap, plus half the spread each way.

Inputs must be simple data objects, such as bars, quotes, and account state, so that LEAN and NautilusTrader wrappers can both supply them later.

Finish with a test that reproduces the blueprint's $5,000 worked table exactly. Use pandas or numpy only where they simplify the code. Ask me before adding any other dependency.
```

## Phase 2: Research on QuantConnect

- **Goal**: A baseline backtest of the rubric on SPY and QQQ, with real costs
- **Time**: 6 weeks, about 18 hours
- **New cost**: $0

### You do

- [ ] Decide the hold-out period now, before seeing any result. Suggested: the most recent two years stay untouched until Phase 3
- [ ] Write that decision down as an architecture decision record

### Checklist

- [ ] Read QuantConnect's published opening range breakout example as a reference
- [ ] Thin LEAN wrapper that feeds bars, quotes, and account state into the rubric and turns verdicts into orders
- [ ] Copy the rubric files into the QuantConnect project. The free plan has no local tool, so this is copy and paste from your repo
- [ ] Set the Interactive Brokers brokerage model so fees and fills follow that broker's rules
- [ ] Entry window, forced close, limit orders, and a stop order with every entry
- [ ] Baseline backtest on the in-sample years only
- [ ] Research log: one line per variation tried, with date, what changed, and the result. The count is needed in Phase 3
- [ ] Export daily returns and the trade list for Phase 3

### Exit criteria

- A baseline backtest exists with commissions and spread included.
- Every position had a stop and was closed by the forced close time.
- The research log is complete and the hold-out years are untouched.
- The rubric code in QuantConnect is identical to the repo.

### Claude Code prompt, Phase 2

``` text
Read CLAUDE.md and docs/blueprint.md first. Show me a short plan in plain language and wait for my approval before changing anything. Use existing libraries before writing custom code. Explain anything technical simply.

Phase 2 goal: a thin LEAN adapter so the rubric can be backtested on QuantConnect's free cloud plan.

Constraints: the free plan has no LEAN CLI and no custom packages, so the adapter and rubric files will be pasted into the QuantConnect web editor. Keep every file small and free of third-party imports that QuantConnect does not provide.

Build:
1. A LEAN algorithm in Python for SPY and QQQ at minute resolution that builds the rubric's input objects from LEAN data, calls the rubric, and acts on the verdict.
2. Use LEAN's Interactive Brokers brokerage model for fees and fills, set as a cash account so settlement rules apply in the backtest. Cap entries at 3 a day. Limit orders only, a stop order placed when an entry fills, scheduled entry window and forced close using LEAN's scheduling.
3. Log every decision record, including rejections, so I can count rejections per check.
4. A research log template in docs with one line per variation.
5. Step by step instructions, written simply, for pasting the files into QuantConnect and running a backtest on the in-sample years only. The hold-out years in the ADR must never be used in this phase.

Reference QuantConnect's published opening range breakout research for structure, but the trading logic must come only from our rubric.
```

## Phase 3: Out-of-sample checks, go or no-go

- **Goal**: An honest answer to "is this real, after costs?"
- **Time**: 3 weeks, about 9 hours
- **New cost**: $0

### You do

- [ ] Before running anything, write the pass marks into a decision record. Suggested: positive return after costs on the hold-out years, Deflated Sharpe Ratio above 0.95, Probability of Backtest Overfitting well under 0.5
- [ ] Make the go or no-go call yourself, against the pass marks you wrote

### Checklist

- [ ] Check pypbo or purgedcv against the worked example in the original paper before trusting it
- [ ] Walk-forward test across the in-sample years
- [ ] One single run on the hold-out years
- [ ] Deflated Sharpe Ratio using the number of variations from the research log
- [ ] Probability of Backtest Overfitting across the variations
- [ ] Ask Claude Code, with the backtest review skills, to argue against the strategy like a sceptical risk manager
- [ ] Write the result and the decision as an architecture decision record

### Exit criteria

- **Go:** every pass mark met. Continue to Phase 4.
- **No-go:** return to Phase 2 with a new idea, at most three times. Each return adds to the variation count, which raises the bar. After three, stop or rethink the approach. You have spent $0.

### Claude Code prompt, Phase 3

``` text
Read CLAUDE.md and docs/blueprint.md first. Show me a short plan in plain language and wait for my approval before changing anything. Use existing libraries before writing custom code. Explain anything technical simply.

Phase 3 goal: test whether the Phase 2 result is real or overfitted. I have already written the pass marks in an ADR. Read it and do not suggest changing them after results are in.

1. Evaluate pypbo and purgedcv. Pick one, and first prove it reproduces a worked example from Bailey and Lopez de Prado's papers. Show me the comparison.
2. From the exported returns and research log, compute walk-forward results, the Deflated Sharpe Ratio using the true number of variations tried, and the Probability of Backtest Overfitting.
3. Produce a one-page plain-language report: what each number means, whether each pass mark was met, and the three strongest reasons to distrust the result.
4. If the claude-trading-skills or claude-code-quant-skills backtest review skills are installed, use them to critique the backtest for look-ahead bias, survivorship bias, and unrealistic fills.

Do not tune anything in this phase. The hold-out data may be used exactly once.
```

## Phase 4: Port and confirm on NautilusTrader

- **Goal**: The same result on a second engine and a second data source
- **Time**: 6 weeks, about 18 hours
- **New cost**: Market data, roughly USD 10 to 15 a month, to confirm

### You do

- [x] Interactive Brokers Canada account opened. Done
- [ ] Turn on two-factor login, enable API access, and create a second username for viewing
- [ ] Set up the free paper trading account
- [ ] Subscribe to real-time US data and note the actual package and price
- [ ] Book the accountant conversation about business income
- [ ] Check the account you opened: taxable, not a TFSA. Confirmed as a cash account. Able to hold US dollars. Tiered commissions selected

### Checklist

- [ ] Pin a specific NautilusTrader version and record it
- [ ] Spike, three hours at most: how far back does Interactive Brokers minute data go for SPY and QQQ? If not far enough, price Databento as the fallback
- [ ] NautilusTrader wrapper that feeds the same rubric, unchanged
- [ ] Risk engine settings for order value cap and order rate limit, and the built-in position sizer checked against the rubric's own sizing
- [ ] Load history into NautilusTrader's data catalog and backtest the same period as Phase 2
- [ ] Compare with the LEAN result: number of trades, win rate, average R, total return after costs
- [ ] Short note explaining any differences

### Exit criteria

- The rubric package was not edited to make the port work.
- Both engines agree on direction and rough size of the result, and the differences are explained.
- If they disagree badly, stop and find out why before going further.

### Claude Code prompt, Phase 4

``` text
Read CLAUDE.md and docs/blueprint.md first. Show me a short plan in plain language and wait for my approval before changing anything. Use existing libraries before writing custom code. Explain anything technical simply.

Phase 4 goal: a NautilusTrader adapter for the same rubric, and a backtest that confirms the QuantConnect result.

1. Pin a NautilusTrader version and record it in an ADR. It is near a 2.0 release, so check the release notes for breaking changes first.
2. Time-boxed spike: using NautilusTrader's Interactive Brokers historical data client against my paper account, find how far back minute bars go for SPY and QQQ. Report back before building further. Fallback is the Databento adapter.
3. Write the adapter as a NautilusTrader Strategy that builds the rubric's input objects and acts on its verdicts. The rubric package must not change. If it seems to need a change, stop and tell me why.
4. This is a cash account: keep the settled-cash check and the 3 entries a day cap active in the backtest. Configure the RiskEngine for max notional per order and order submit rate from our settings file. Compare the built-in fixed-risk PositionSizer with the rubric's sizing on the $5,000 worked example.
5. Run the backtest for the Phase 2 period and produce a side by side comparison with the LEAN export.

Broker credentials go in the environment file only. Use the paper account only.
```

## Phase 5: Operations layer

- **Goal**: Database, dashboard, alerts, and safety nets, all working on your PC against the paper account
- **Time**: 5 weeks, about 15 hours
- **New cost**: $0. Supabase, Healthchecks.io, and Telegram are free at this size

### You do

- [ ] Install Docker Desktop, which needs administrator rights on Windows
- [ ] Create a Supabase project on the free plan
- [ ] Create a Telegram bot and a Healthchecks.io account
- [ ] Create a read-only flex query in Interactive Brokers account management for the daily reconciliation

### Checklist

- [ ] Database tables for orders, fills, positions, account snapshots, rubric decisions, settings requests, a halt flag, and heartbeats
- [ ] Row level security on every table, explicit grants, a read-only database role for Grafana, and the service key stored only in the environment file
- [ ] Bridge inside the wrapper that writes rows and reads the halt flag. If the database is unreachable, trading continues and rows wait in a local file
- [ ] Daily heartbeat row, which also stops the free Supabase project pausing after seven quiet days
- [ ] Weekly database backup with a scheduled GitHub Action, because the free plan has none
- [ ] Telegram alerts through Apprise: fills, stops, limit trips, halt, daily summary
- [ ] Healthchecks.io ping from the engine
- [ ] Daily reconciliation script using ibflex that compares the journal with the broker's statement
- [ ] Startup guard: refuse to start if trading mode and broker connection disagree
- [ ] Small component that sets the halted state at the 1% daily loss
- [ ] Grafana container with the eight panels from the blueprint
- [ ] Runbook, one page each: start, stop, emergency halt, weekly login, restore from backup

### Exit criteria

- Every Grafana panel shows real paper data.
- Every alert type has reached your phone, including a deliberate limit trip.
- Halt test passed: setting the flag stops new orders, and stops stay at the broker.
- Outage test passed: with the database unreachable, the engine keeps trading and catches up afterwards.
- No broker credentials anywhere in the database.

### Claude Code prompt, Phase 5

``` text
Read CLAUDE.md and docs/blueprint.md first. Show me a short plan in plain language and wait for my approval before changing anything. Use existing libraries before writing custom code. Explain anything technical simply.

Phase 5 goal: the operations layer from the blueprint's "Dashboard" and "Operating the system" sections, running locally against the IBKR paper account.

Design rule that overrides convenience: the trading engine must never depend on the database. If Supabase is unreachable, trading continues, rows queue in a local file, and they are written when the connection returns.

Build in this order, testing each before the next:
1. Supabase schema as SQL migrations: orders, fills, positions, account_snapshots, rubric_decisions, settings_requests, control_flags, heartbeats. Row level security on, explicit grants, a read-only role for Grafana. New Supabase projects need explicit grants for the Data API, so check the current docs.
2. The bridge inside the NautilusTrader adapter, subscribed to the message bus, with the local queue.
3. Startup guard and the daily loss component that sets TradingState to HALTED.
4. Alerts with Apprise to Telegram, and a Healthchecks.io ping.
5. Daily reconciliation with ibflex and the IBKR Flex Web Service.
6. A docker compose file for the engine, IB Gateway, and Grafana, with Grafana provisioned from files in the repo so the dashboard is version controlled.
7. A scheduled GitHub Action that backs up the database weekly.
8. Runbooks in docs, one page each, written for someone who is not a tooling expert.

Broker credentials must never be written to the database. The Supabase service key lives only in the environment file.
```

## Phase 6: Deploy and paper trade

- **Goal**: The whole system running unattended on a server, trading pretend money
- **Time**: 2 weeks to deploy, then at least 6 weeks running at about an hour a week
- **New cost**: Server, about $5 to $10 a month

### You do

- [ ] Rent one small Linux cloud server
- [ ] Approve the Interactive Brokers login on your phone about once a week
- [ ] Look at the Grafana board most market days, and read the daily summary

### Checklist

- [ ] Server hardened: login by key only, firewall closed to everything except that login, automatic security updates
- [ ] Docker compose stack deployed, environment file created by hand on the server
- [ ] Grafana reached through a secure tunnel or private network tool, never an open web address
- [ ] One-command deploy and one-command halt, both in the runbook
- [ ] Weekly review: Claude Code reads the week's decision records and reports patterns, rejections per check, and anything odd
- [ ] Track the paper exit criteria from the blueprint every week

### Exit criteria, from the blueprint

- Dozens of trades, and at least one rough market day lived through.
- One full week with no bugs.
- Journal and broker statement match exactly, every day.
- Forced close fired every day.
- Every alert type arrived, including a halt test on the server.
- Results within a sensible range of the backtest for the same period.

### Claude Code prompt, Phase 6

``` text
Read CLAUDE.md and docs/blueprint.md first. Show me a short plan in plain language and wait for my approval before changing anything. Use existing libraries before writing custom code. Explain anything technical simply.

Phase 6 goal: deploy the Phase 5 stack to one small Linux cloud server and run it against the IBKR paper account.

1. Give me a plain-language server setup guide I can follow line by line: key-only login, firewall closed except for that login, automatic security updates, Docker installed.
2. A one-command deploy script that pulls the repo and restarts the stack only when the market is closed, and a one-command halt script. Add both to the runbook.
3. Show me the simplest safe way to view Grafana from my phone and laptop without opening it to the internet. Compare a secure tunnel with a private network tool and recommend one.
4. A weekly review routine: read the week's rubric decisions and fills from the database, then report counts of rejections per check, realised R-multiples, any day the forced close or reconciliation failed, and anything unusual. Report only. Never change settings.

The environment file on the server is created by me by hand. Never print, log, or commit its contents. Trading mode stays paper.
```

## Phase 7: Live, small

- **Goal**: Learn what real fills cost, with as little at stake as possible
- **Time**: 8 weeks or more, about an hour a week
- **New cost**: Commissions, about USD 0.70 in and out per trade

### You do, and only you

- [ ] Confirm every Phase 6 exit criterion is met
- [ ] Have the accountant conversation
- [ ] Confirm Interactive Brokers applies the new intraday margin rules to your account
- [ ] Decide the slice of the budget to start with, and write down in advance the loss on that slice at which you halt and review
- [ ] Fund the account and convert to US dollars once, not per trade
- [ ] Change the two settings, trading mode and broker connection, on the server yourself

### Checklist

- [ ] First live day: watch the first entry, its stop at the broker, and the forced close
- [ ] Weekly comparison of live fills against paper fills for the same signals
- [ ] Weekly review as in Phase 6
- [ ] Reconciliation clean every day

### Exit criteria

- Live results track paper results within a tolerance you set in advance, over a meaningful number of trades.
- No limit breach, no unprotected position, no reconciliation mismatch.
- A decision record for whatever comes next: scale up, stay small, or stop.

### Claude Code prompt, Phase 7

``` text
Read CLAUDE.md and docs/blueprint.md first. Show me a short plan in plain language and wait for my approval before changing anything. Use existing libraries before writing custom code. Explain anything technical simply.

Phase 7 goal: support small live trading. You do not switch the system to live and you do not edit the environment file. I do both by hand.

1. Write a pre-live checklist in docs that I tick off: Phase 6 exit criteria, accountant, funding, the two settings, the pre-agreed halt-and-review loss for the starting slice.
2. Build a weekly live-versus-paper comparison from the database: fill price versus signal price, slippage per trade in dollars and in R, and total cost drag.
3. Extend the weekly review with a plain-language verdict on whether live is tracking paper within my tolerance.

If you notice anything that looks like a limit breach, an unprotected position, or a reconciliation mismatch, put it at the very top of your report.
```

## Later phases

Each gets its own plan in this same template when its time comes, and each goes through the full stage gates.

| Phase                       | What it adds                                                                                                        | Depends on                                                     |
|-----------------------------|---------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------|
| Your React UI               | View activity and profit or loss, request setting changes, halt button. Uses the Supabase login and the same tables | A few weeks of Grafana use, so you know which screens you want |
| High relative volume stocks | Universe selection and the relative volume component doing real work                                                | Phase 7 stable                                                 |
| Crypto on Kraken Pro        | Kraken adapter and a slower, weekly-horizon model                                                                   | Kraken account, fee-aware research                             |
| Options                     | New instrument type and its own sizing rules                                                                        | A larger account, realistically                                |

## Cost as you go

| Phases                              | Monthly                                                                |
|-------------------------------------|------------------------------------------------------------------------|
| 0 to 3                              | $0                                                                    |
| 4 and 5                             | Market data, roughly USD 10 to 15                                      |
| 6 and 7                             | About $15 to $25, plus commissions once live                         |
| If Supabase's free plan is outgrown | Add $25 for its Pro plan, which also adds backups and removes pausing |

## Still to verify, and where

| Item                                                                                                        | Phase |
|-------------------------------------------------------------------------------------------------------------|-------|
| pypbo or purgedcv reproduces the papers' worked examples                                                    | 3     |
| Interactive Brokers data package, price, and minimum balance to subscribe                                   | 4     |
| Settlement rules and the margin account minimum, confirmed with Interactive Brokers Canada for your account | 4     |
| Depth of Interactive Brokers minute history, with Databento as fallback                                     | 4     |
| NautilusTrader version to pin, given the 2.0 release candidate                                              | 4     |
| Apprise library, and Supabase's current grant requirements and free limits                                  | 5     |
| Interactive Brokers has moved to the new intraday margin rules                                              | 7     |

## Sources added for this plan

- [Supabase: pricing and free plan pausing](https://supabase.com/pricing), and [2026 free tier limits and the new grants requirement](https://www.itpathsolutions.com/supabase-free-tier-limits)
- [Interactive Brokers: next-day settlement and cash accounts](https://www.interactivebrokers.com/campus/traders-insight/securities/stocks/t1-settlement-what-it-means-for-traders-and-investors/)
- All other sources are listed in the blueprint.

Source: the published page at https://claude.ai/artifact/1VugqdgRx7gnTNoWB6P4Zk. This Markdown copy was generated from it on 18 September 2026.
