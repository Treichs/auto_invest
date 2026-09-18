# Automated trading system blueprint

An autonomous system that trades US index ETFs through Interactive Brokers, with every trade passing a two-tier rubric and hard limits that sit outside the strategy. Built almost entirely from existing open-source parts.

Final blueprint, revision 2.2. Research dates 17 to 18 September 2026. Adds the database hub, the dashboard phasing, and how you operate the system. Engineering guidance only, not financial or tax advice. Next document: the build plan.

1.  **Market data**: Live prices from Interactive Brokers
2.  **Universe**: A short fixed list of index ETFs to start
3.  **Signal score**: Rubric tier two. Five evidence-based components
4.  **Position sizing**: Size from risk per trade and stop distance, inside the caps
5.  **Must-pass checks and risk engine**: Rubric tier one. Any fail vetoes the trade. Fails closed
6.  **Execution**: Limit orders only. Protective stop rests at the broker the moment an entry fills
7.  **Broker**: Interactive Brokers Canada, US-listed securities, IB Gateway

Alongside every stage: monitoring, alerts, kill switch.

## Decisions, locked

| Decision               | Choice                                                                  | Main reason                                                                            |
|------------------------|-------------------------------------------------------------------------|----------------------------------------------------------------------------------------|
| Goal                   | Return after costs, adjusted for risk                                   | "Highest daily profit" is the goal most prone to fitting the past by accident          |
| Autonomy               | Fully autonomous inside hard limits                                     | Your requirement                                                                       |
| Broker                 | Interactive Brokers Canada                                              | Only route found that lets a Canadian resident send automated orders                   |
| Account                | Taxable cash account, holding US dollars                                | Courts have ruled day trading in a TFSA is taxable business income                     |
| Research engine        | LEAN on QuantConnect's free plan                                        | Unlimited backtests with data included, at $0                                         |
| Paper and live engine  | NautilusTrader, self-hosted                                             | Free, with a risk engine outside the strategy. LEAN needs a paid seat to run live      |
| Code structure         | Ports and adapters                                                      | Rubric is plain Python, so moving between engines is a small job                       |
| Language               | Python                                                                  | Both engines and every supporting tool use it                                          |
| First market           | Index ETFs, starting with SPY and QQQ                                   | Strongest published evidence, tightest spreads, no stock-picking code                  |
| Later markets          | High relative volume stocks, then crypto on Kraken Pro, then options    | Each adds cost and complexity, so each waits its turn                                  |
| Hosting                | Your PC for research. Small cloud server with Docker for paper and live | A home PC sleeps, updates, and drops connections                                       |
| Database               | One Postgres database, hosted on Supabase, between the engine and any screen | The engine and the screens never connect directly, so a screen can never break trading |
| Dashboard, first build | Grafana, view only                                                      | Prebuilt and working in an afternoon, which is what the paper gate needs               |
| Dashboard, later phase | Your own React UI to view activity and change settings                  | The only option that gives a control panel. Built once you know which screens you want |
| Claude's role          | Builds the system and reviews the journal after the close               | Decisions must be replayable code, so no language model in the order path              |

## Your three numbers, recommended

| Setting                       | Recommended start   | Why                                                                                                                                                       |
|-------------------------------|---------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|
| What to trade first           | Index ETFs only     | The intraday momentum evidence is peer reviewed and specific to index ETFs. Spreads are the tightest in the market, which matters most on a small account |
| Risk on any single trade      | 0.5% of the account | Half the common 1% rule. It lines up with the position cap below, so the two limits agree instead of fighting                                             |
| Daily loss that halts trading | 1% of the account   | Two full-risk losses and the system stops for the day. A 2% or 3% limit would almost never trigger at this trade size, so it would protect nothing        |

Supporting limits carried as starting assumptions: no borrowed money, at most 25% of the account in one position, at most 80% invested in total, at most 3 entries a day using settled cash only, entries between 10:00 and 15:30 Eastern, everything closed by 15:50. All of these live in one settings file and are tuned only through the stage gates.

### How the limits play out on $5,000

|                                       | Tight stop, 0.4% away             | Wide stop, 2% away                 |
|---------------------------------------|-----------------------------------|------------------------------------|
| Position size                         | $1,250. The 25% cap binds        | $1,250. Both limits agree         |
| Money at risk                         | $5, which is 0.1% of the account | $25, which is 0.5% of the account |
| Commission in and out, about USD 0.70 | 14% of the amount risked          | About 3% of the amount risked      |

### What this table is telling you

On an account this size, without borrowing, the position cap decides trade size more often than the risk rule does. With tight stops, fees take a large bite out of every trade before the market moves. Expect the "trade beats its costs" check to reject many tight-stop trades, and expect research to favour setups with room to run. Interactive Brokers caps tiered commissions at 1.0% of trade value with a USD 0.35 minimum, so fees scale sensibly on small orders but never reach zero.

## Findings that shaped the plan

### The $25,000 day-trading minimum is gone

Replaced on 4 June 2026 by intraday margin rules. Accounts need $2,000 in equity to borrow, and below that trade with cash only. Brokers have until October 2027 to switch, so confirm Interactive Brokers has.

### A TFSA is the wrong home

The Tax Court in 2023 and the Federal Court of Appeal in 2024 held that day trading in a TFSA is carrying on a business, and the gains are taxable. Ask an accountant whether gains in the taxable account will count as business income too.

### Wealthsimple cannot run this

No official API, and it closes accounts that automate. A Canadian regulator rule bars self-directed brokers from accepting orders from a client's own automated system. Interactive Brokers Canada applies it to Canadian-listed stocks only, so the system trades US-listed securities.

### LEAN is free to research on, not to run live

The tool that runs LEAN on your own machine needs a paid QuantConnect seat, about $60 a month. On a $5,000 account that is roughly 16% to 20% a year, which fails the rubric's own cost test.

### Interactive Brokers has two doors

The web route needs a browser login every day and cannot officially be automated. IB Gateway with the TWS API needs a phone approval about once a week. The system uses IB Gateway.

### The odds are poor, so proof comes first

In the largest study of retail day traders, 97% of those who persisted 300 days lost money. A study of 97 published predictors found returns 58% lower after publication. The rubric improves discipline and odds. It cannot promise profit. Stage gates decide whether real money is ever used.

## Architecture

Event-driven: each new price or fill triggers the next step. Strategy logic decides what to do, execution handles doing it reliably, and the risk engine can veto either. The stage names above are neutral. This table maps them to each engine's own terms so the docs and examples line up.

| Stage            | In LEAN, for research                               | In NautilusTrader, for paper and live                                |
|------------------|-----------------------------------------------------|----------------------------------------------------------------------|
| Market data      | Data feed                                           | Data engine with the Interactive Brokers data client                 |
| Universe         | Universe selection model                            | Instrument list in the strategy config                               |
| Signal score     | Alpha model, score becomes the insight's confidence | Strategy component calling your rubric functions                     |
| Position sizing  | Portfolio construction model                        | Built-in fixed-risk position sizer                                   |
| Must-pass checks | Risk management model                               | Risk engine, plus your rubric functions before an order is submitted |
| Execution        | Execution model                                     | Execution engine with the Interactive Brokers execution client       |
| Kill switch      | Liquidate and quit                                  | Trading state set to halted                                          |

### Where everything runs

- **Your PC**: VS Code with Claude Code, Git, QuantConnect research and backtests in the browser
- **Small cloud server, Docker**: Always on during market hours. One container each
  - NautilusTrader with your rubric
  - IB Gateway, managed by the engine
  - Bridge that writes trades, positions, and decisions to the database
  - Grafana, view only, private access
- **Outside services**: Interactive Brokers, the Postgres database, Healthchecks.io heartbeat alarm, Telegram alerts, your phone for the weekly login approval

## The trade rubric

1.  **Candidate trade appears**: The strategy spots a possible entry.
2.  **Must-pass checks**: Eight yes or no checks. One "no" rejects the trade. Missing data counts as "no".
3.  **Signal score**: Five components, equal weight to start. Below the threshold, rejected.
4.  **Size by risk and volatility**: 0.5% risk, inside the 25% and 80% caps.
5.  **Order sent, decision logged and published**: Every check result is recorded, including for rejected trades, and shown on the dashboard.

### Tier one: must-pass checks

| Check                    | Passes when                                                                                           | Supplied by                                  |
|--------------------------|-------------------------------------------------------------------------------------------------------|----------------------------------------------|
| Data is sane             | Quote is fresh, price inside a reasonable band                                                        | Your rubric                                  |
| Instrument is eligible   | US-listed, not halted, on the approved list                                                           | Settings file                                |
| Market is liquid         | Spread under a cap, volume over a floor                                                               | Your rubric                                  |
| Trade beats its costs    | Expected move is a set multiple of commission plus spread                                             | Your rubric                                  |
| Exit is defined          | Stop price set before entry, and it will rest at the broker                                           | Engine order types                           |
| Risk budget has room     | Order value, per-symbol cap, total exposure, entries today, enough settled cash                       | Risk engine, plus your entries-per-day count |
| Daily loss limit not hit | Today's loss under 1% of the account                                                                  | Small component that sets the halted state   |
| System is healthy        | Broker connected, positions match the broker, not already holding the symbol, inside the entry window | Engine reconciliation and clock              |

### Tier two: signal score

| Component                        | What the research found                                                                                             | Evidence                                                           |
|----------------------------------|---------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------|
| Trend direction                  | An asset's own past return tends to persist for 1 to 12 months. Trade with it                                       | Strong. Peer reviewed, replicated                                  |
| Intraday momentum                | On the S&P 500 ETF and ten other heavily traded ETFs, the first half-hour's direction predicts the last half-hour's | Strong for index ETFs. Peer reviewed                               |
| Volatility and volume conditions | That effect is stronger on volatile, high-volume, and major news days                                               | Strong. Same study                                                 |
| Opening range breakout           | Entering on a break of the opening range, studied on QQQ and on 7,000 US stocks, 2016 to 2023                       | Moderate. Working papers, authors run a trading education business |
| Relative volume                  | Activity far above normal drove most of the breakout results. Central once stocks are added                         | Moderate. Same working papers                                      |

### What makes it hardened

- **Fails closed.** A check that cannot be evaluated counts as failed.
- **Few numbers to tune.** Five components at equal weight. The threshold comes from your own out-of-sample tests, never from a paper's headline result.
- **Limits sit outside the strategy.** The risk engine denies orders regardless of what the strategy wants.
- **Versioned.** Any change to a check, weight, or threshold goes back through the stage gates.
- **Startup guard.** Refuses to start if its paper or live setting disagrees with the broker connection.
- **Broker is the source of truth.** Positions are reconciled at startup and before entries. A separate daily check compares the journal with the broker's own statement.
- **Flat by the close.** No entries after the cutoff, all positions closed before the bell.

### Hard limits, by their industry names

| FIA control               | Here                                                            |
|---------------------------|-----------------------------------------------------------------|
| Maximum order size        | Risk engine order value cap                                     |
| Maximum intraday position | 25% per symbol, 80% in total                                    |
| Price tolerance           | Limit orders only, priced close to the market                   |
| Execution throttle        | Risk engine order rate limit, plus 3 entries a day              |
| Cancel on disconnect      | Stops rest at the broker, so protection survives a dropped link |
| Kill switch               | Halted trading state, plus a documented manual stop             |
| Drop copy reconciliation  | Daily statement check through the Flex Web Service              |

## Stage gates before real money

1.  **Research**: On QuantConnect. Record every variation tried, because the count matters later.
2.  **Backtest with real costs**: Commissions, spreads, slippage. A strategy that only works with free trading does not work.
3.  **Out-of-sample checks**: Walk-forward testing, then Deflated Sharpe Ratio and Probability of Backtest Overfitting.
4.  **Port and confirm**: Move the wrapper to NautilusTrader and re-run the backtest on Interactive Brokers data. A second engine and data source agreeing is strong evidence the result is real.
5.  **Paper trading**: Live market, pretend money, the full system running on the server.
6.  **Live, small**: A slice of the budget with the tightest limits. Measures what real fills cost.
7.  **Scale up**: Only after live results track paper results.

### What paper trading is

Trading with pretend money against the real, live market. Same code, same prices, same broker connection, but orders go to a simulated account that comes free with your Interactive Brokers account.

|                   | Backtest                          | Paper trading                | Live, small              |
|-------------------|-----------------------------------|------------------------------|--------------------------|
| Data              | Past, replayed in seconds         | Live, one market day per day | Live                     |
| Money             | None                              | Pretend                      | Real, small slice        |
| Question answered | Would the idea have worked?       | Does the whole system work?  | What do real fills cost? |
| Blind spot        | Logins, outages, alerts, restarts | Fills are optimistic         | Small sample at first    |

### Exit criteria for the paper gate

- Dozens of trades logged, and at least one rough market day lived through.
- One full week with no bugs.
- Journal and the broker's statement match exactly, every day.
- Forced close fired every day.
- Every alert type arrived on your phone, including a deliberate limit trip and a kill switch test.
- Results sit within a sensible range of the backtest for the same period.

## Tech stack and reuse map

| Need                                       | Tool                                                                          | Custom code                          |
|--------------------------------------------|-------------------------------------------------------------------------------|--------------------------------------|
| Editor and build help                      | VS Code with Claude Code                                                      | None                                 |
| Version control                            | Git, private GitHub repository                                                | None                                 |
| Research and backtests                     | LEAN on QuantConnect's free plan                                              | Thin wrapper                         |
| Paper and live engine                      | NautilusTrader in Docker, version pinned                                      | Thin wrapper                         |
| Broker link and gateway login              | NautilusTrader's Interactive Brokers adapter with the gnzsnz IB Gateway image | None                                 |
| Order caps, rate limit, kill switch states | NautilusTrader risk engine                                                    | Settings only                        |
| Position size from risk                    | Rubric function, checked against NautilusTrader's position sizer in Phase 4  | One function                         |
| Overfitting statistics                     | pypbo or purgedcv                                                             | None                                 |
| Performance reports                        | pyfolio-reloaded                                                              | None                                 |
| Phone alerts                               | Telegram through the Apprise library                                          | A few lines                          |
| Heartbeat alarm                            | Healthchecks.io                                                               | One web call                         |
| Independent reconciliation                 | Interactive Brokers Flex Web Service with ibflex                              | Short daily script                   |
| Database hub                               | Postgres                                                                      | Small bridge in the engine wrapper   |
| Dashboard, first build                     | Grafana in Docker, reading Postgres                                           | None. Panels are arranged, not coded |
| Dashboard, later phase                     | React, with Supabase as the home for login and the database connection        | Large. A project of its own          |
| After-hours review, optional               | TradeTally or Power BI Desktop                                                | None                                 |
| Backtest review help                       | Claude Code skills from tradermonty and shakeebshaan                          | None                                 |

### The whole custom code budget

1.  Five signal score functions. This is the strategy itself.
2.  Eight must-pass checks as plain functions. Four of them have no engine equivalent: data sanity, liquidity, trade beats its costs, entries-per-day cap.
3.  One small component that halts trading at the daily loss limit.
4.  Two thin wrappers, one per engine, that call items 1 to 3 and publish each rubric decision as an event.
5.  A short daily reconciliation script.
6.  A small bridge that writes clean rows to the database and reads settings and the halt flag from it.

The React UI is a later phase with its own budget. Items 1 to 3 are plain Python that knows nothing about either engine. That is the ports and adapters pattern. It lets the rubric be tested on its own, and it keeps the move from LEAN to NautilusTrader small.

## Dashboard

NautilusTrader has no dashboard and lists user interfaces as out of scope. So the system puts one Postgres database in the middle. The engine writes trades, positions, profit and loss, and rubric decisions into it. Any screen reads from it. The engine and the screens never connect directly, so a screen can crash without touching trading, and the trading server needs no ports open to the internet.

The database is not needed for the engine to trade. It is needed for any screen that shows history, and for changing settings from a screen later.

### First build: live status board in Grafana

Grafana is a free, open-source dashboard app. You point it at the database and arrange panels, numbers, gauges, charts, tables, by dragging. It has its own login and can send alerts. It is a window: it shows everything and changes nothing.

| Panel                                         | Why it earns a place                                  |
|-----------------------------------------------|-------------------------------------------------------|
| Heartbeat and broker connection               | First thing to check. Green or red                    |
| Trading state: active, reducing only, halted  | Shows whether a limit has tripped                     |
| Today's profit or loss against the 1% limit   | How close the system is to stopping itself            |
| Risk budget used                              | Exposure, cash reserve, entries today against the cap |
| Open positions with entry, stop, unrealised R | Confirms every position has a stop at the broker      |
| Rubric decisions, and which check rejected    | Shows the rubric working                              |
| Recent orders and fills                       | What actually happened                                |
| Last reconciliation result                    | Journal matches the broker, or not                    |

### After-hours review, optional

The daily report lands on your phone either way. When you want to dig, point TradeTally or Power BI Desktop at the trade history. Neither needs code, and neither is part of the first build.

### Later phase: your own React UI

A control panel that views activity and changes settings, built after the paper gate once you know which screens you want. It reads and writes the same database, so nothing built for Grafana is wasted.

| Rule                                  | How it works                                                                                                                                           |
|---------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|
| Two tiers of settings                 | Operating settings are editable in the UI. Hard ceilings live only in a file on the server, and the UI can never raise a limit above them              |
| Changes are requests                  | The UI saves a request. The engine applies it at the next restart after the close, checks it against the ceilings, and logs it with the rubric version |
| Halt button allowed                   | Stopping is always a tightening action, so it is safe to trigger from the UI                                                                           |
| Paper to live stays off the UI        | That switch remains a deliberate change on the server, protected by the startup guard                                                                  |
| No broker credentials in the database | They stay on the trading server only                                                                                                                   |

### Ground rules

- **Grafana is view only.** No trade or settings controls.
- **Private.** Reached through a private network tool or secure tunnel, never an open web address.
- **Separate container.**
- **Second Interactive Brokers username for viewing.** One trading session is allowed per username, so logging in as the system's user can knock it offline.

## Operating the system

You operate it, you do not program it. How far a change travels before reaching live depends on how risky it is.

| Kind of change                | Examples                                                  | Path to live                                                                                                        |
|-------------------------------|-----------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------|
| Tighten a limit               | Lower a cap, remove a symbol, shorten the entry window    | Next restart after the close. Tightening never needs proof                                                          |
| Loosen or retune              | Raise a cap, change rubric weights or the score threshold | Backtest, then paper, then live                                                                                     |
| New symbol                    | Another index ETF                                         | Add to the approved list, backtest, paper, live                                                                     |
| New setup or signal component | A mean reversion setup, a new score component             | New plain Python function with tests, full stage gates, then live at small size. The engine wrapper does not change |
| New market                    | Crypto, then options                                      | A small project each: account, adapter, sizing rules, full stage gates                                              |

### Day to day

- **Watch** the Grafana board.
- **Get told** by Telegram: fills, stops, limit trips, daily summary. Healthchecks.io alarms if the system goes quiet.
- **One chore.** Approve the Interactive Brokers login on your phone about once a week.
- **Emergency stop.** One documented command halts the engine. Stops already rest at the broker, so positions stay protected even if the server is unreachable.

### Changing settings

Every threshold, cap, time window, and symbol lives in one settings file in Git. Edit it yourself or describe the change to Claude Code and review what it shows you. Changes apply at a restart after the close, never while the market is open. Each version is tagged, and the journal records which rubric version made each trade.

### Moving from paper to live

1.  Tick off the paper exit criteria.
2.  See the accountant.
3.  Fund the account.
4.  Change the two settings, trading mode and broker connection. The startup guard refuses to run unless both agree.
5.  Start at live, small, with a slice of the budget.

## Accounts and costs

| Account                                                        | When                             | Cost to hold                          |
|----------------------------------------------------------------|----------------------------------|---------------------------------------|
| QuantConnect, GitHub, Claude with Claude Code                  | Now                              | Free, free, your existing plan        |
| Interactive Brokers Canada, with a second username for viewing | Before the port-and-confirm gate | No minimum, no platform fee           |
| Cloud server provider, Telegram, Healthchecks.io               | Before the paper gate            | About $5 to $10 a month, free, free |
| Accountant                                                     | Before going live                | One consultation                      |
| Kraken Pro                                                     | Crypto phase                     | Free to hold                          |

| Stage                                 | Fixed monthly                                  | Per trade                                                |
|---------------------------------------|------------------------------------------------|----------------------------------------------------------|
| Research through out-of-sample checks | $0                                            | None                                                     |
| Port, confirm, and paper trading      | About $15 to $25: server plus real-time data | None. Simulated                                          |
| Live                                  | Same, about 4% to 6% of $5,000 a year         | About USD 0.70 in and out. USD 2 per currency conversion |
| Crypto phase                          | No extra                                       | Kraken Pro base tier 0.25% or 0.40% each way             |

## Ruled out, and why

| Option                                                              | Reason                                                                                      |
|---------------------------------------------------------------------|---------------------------------------------------------------------------------------------|
| Wealthsimple, Alpaca, Questrade                                     | No API and account closure, does not accept Canadians, same regulator rule as Wealthsimple  |
| TFSA                                                                | Day trading inside one is taxable business income                                           |
| LEAN for live trading                                               | Paid seat costs too much against a small account. Reasonable at roughly five times the size |
| Lumibot                                                             | No limits outside the strategy, and its default broker route needs a daily browser login    |
| Backtrader, Zipline, vectorbt, backtesting.py                       | Unmaintained, or research only with no live trading                                         |
| A language model placing trades                                     | Cannot be replayed over history, so cannot pass the stage gates                             |
| Risk rules written as instructions                                  | An instruction can be skipped. A risk engine cannot                                         |
| Free Yahoo data for live signals, market orders, home PC scheduling | Unreliable data, poor fills on a small account, machine sleep and outages                   |
| React UI in the first build                                         | Would delay the first useful paper test by weeks. Moved to a later phase, not dropped       |

## To verify during the build

1.  Interactive Brokers real-time data package, price, and any minimum balance to subscribe. Budgeted at USD 10 to 15 a month.
2.  Whether Interactive Brokers historical data reaches far enough back, at intraday detail, for the port-and-confirm backtest. Databento is the fallback.
3.  Whether Redis is needed at all once the bridge writes straight to Postgres.
4.  The Apprise library, and the two small overfitting libraries, against the papers' worked examples.
5.  That Interactive Brokers has switched to the new intraday margin rules.
6.  Settlement rules for your cash account, confirmed with Interactive Brokers Canada. The plan assumes sale proceeds are usable the next business day, which sets the entries cap at 3. A margin account, USD 2,000 minimum, is the later option and would go through the stage gates.
7.  NautilusTrader is at a version 2.0 release candidate. Pin the version and read the release notes before upgrading.
8.  Whether direct crypto trading is open to Ontario residents at Interactive Brokers. Assumed no, hence Kraken.

## Sources

- [QuantConnect: Algorithm Engine](https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/algorithm-engine) and [Algorithm Framework overview](https://quantconnect.com/docs/algorithm-framework/overview)
- [QuantConnect: pricing and plan features](https://www.quantconnect.com/pricing/), with prices from [NewTrading](https://www.newtrading.io/quantconnect-review/) and [Climb](https://climbtheladder.com/what-is-quantconnect-algo-trading-platform-explained/) reviews
- [Interactive Brokers Canada: commissions overview](https://www.interactivebrokers.ca/en/pricing/commissions-home.php), [US stock trading costs for Canadian residents](https://www.interactivebrokers.ca/en/trading/us-stock-trading-costs-for-canadian-resi.php), and [market data pricing](https://www.interactivebrokers.ca/en/pricing/market-data-pricing.php)
- [BrokerChooser: Alpaca availability in Canada](https://brokerchooser.com/broker-reviews/alpaca-trading-review/alpaca-trading-canada) and [Kraken Pro fee schedule summary](https://us.fitgap.com/products/015126/kraken)
- [NautilusTrader: message bus and Redis streaming](https://docs.nautilustrader.io/concepts/message_bus.html), [release notes on SQL cache, heartbeat, and snapshots](https://github.com/nautechsystems/nautilus_trader/releases/tag/v1.231.0), and [live trading and startup reconciliation](https://nautilustrader.io/docs/latest/concepts/live/)
- [Redis data source for Grafana](https://github.com/RedisGrafana/grafana-redis-datasource), [community NautilusTrader projects](https://github.com/topics/nautilustrader), and [TradeTally](https://github.com/GeneBO98/tradetally/wiki)
- [LEAN CLI: live deploy, paid tier requirement](https://www.lean.io/docs/v2/lean-cli/api-reference/lean-live-deploy) and [QuantConnect forum: Researcher seat for local live](https://www.quantconnect.com/forum/discussion/17128/running-lean-live-locally/)
- [NautilusTrader: Interactive Brokers integration](https://nautilustrader.io/docs/latest/integrations/interactive_brokers/), [execution and risk checks](https://nautilustrader.io/docs/latest/concepts/execution/), and [repository](https://github.com/nautechsystems/nautilus_trader)
- [Lumibot repository](https://github.com/Lumiwealth/lumibot) and [its Interactive Brokers setup notes](https://lumibot.lumiwealth.com/brokers.interactive_brokers.html)
- [LEAN: supported risk management models](https://quantconnect.com/docs/v2/writing-algorithms/algorithm-framework/risk-management/supported-models)
- [awesome-systematic-trading](https://github.com/paperswithbacktest/awesome-systematic-trading), [Healthchecks.io](https://healthchecks.io/about), [ibflex](https://github.com/csingley/ibflex), and [AWS: algorithmic trading reference architecture](https://docs.aws.amazon.com/reference-architecture-diagrams/latest/algorithmic-trading-on-aws/algorithmic-trading-on-aws.html)
- [LEAN engine: asset classes, licence, languages](https://www.lean.io/)
- [NautilusTrader: architecture](https://nautilustrader.io/docs/latest/concepts/architecture/) and [overview](https://nautilustrader.io/docs/latest/concepts/overview/)
- [QuantInsti: parts of an automated trading system](https://www.quantinsti.com/articles/automated-trading-system/)
- [FIA: Best practices for automated trading risk controls and system safeguards (2024)](https://www.fia.org/sites/default/files/2024-07/FIA_WP_AUTOMATED%20TRADING%20RISK%20CONTROLS_FINAL_0.pdf)
- [FINRA Regulatory Notice 26-10: intraday margin standards](https://www.finra.org/rules-guidance/notices/26-10) and [investor explainer](https://www.finra.org/investors/insights/intraday-margin-requirements)
- [Canadian Tax Foundation: TFSA active trading ruling](https://www.ctf.ca/EN/EN/Newsletters/Canadian_Tax_Focus/2023/2/230203.aspx) and [Fidelity Canada: what counts as day trading](https://www.fidelity.ca/en/insights/articles/day-trading-in-canada/)
- [Interactive Brokers Canada: TFSA rules](https://www.interactivebrokers.ca/en/index.php?f=13406&p=tfsa) and [fractional trading](https://www.interactivebrokers.ca/en/trading/fractional-trading.php)
- [Canadian Securities Administrators: authorised crypto platforms](https://www.securities-administrators.ca/crypto-platforms-regulation-and-enforcement-actions/crypto-platforms-authorized-to-do-business-with-canadians/)
- [Bailey and López de Prado: The Deflated Sharpe Ratio](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551) and [The Probability of Backtest Overfitting](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253)
- [Chague, De-Losso, Giovannetti: Day trading for a living?](https://ideas.repec.org/p/fgv/eesptd/525.html)
- [Wealth Awesome: Wealthsimple API status](https://wealthawesome.com/wealthsimple-api), [QuantConnect forum: Interactive Brokers Canada API notice](https://www.quantconnect.com/forum/discussion/7303/canadians-not-allowed-to-use-interactive-brokers-api-anymore/), and [SnapTrade: personal use](https://docs.snaptrade.com/docs/personal-vs-commercial)
- [Gao, Han, Li, Zhou: Market intraday momentum](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2440866)
- [Moskowitz, Ooi, Pedersen: Time series momentum](https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf)
- [Zarattini, Barbon, Aziz: opening range breakout and stocks in play](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4729284) and [QuantConnect's LEAN rebuild](https://www.quantconnect.com/research/18444/opening-range-breakout-for-stocks-in-play/)
- [Crypto momentum review citing Liu and Tsyvinski (2021)](https://acfr.aut.ac.nz/__data/assets/pdf_file/0009/918729/Time_Series_and_Cross_Sectional_Momentum_in_the_Cryptocurrency_Market_with_IA.pdf)
- [McLean and Pontiff: Does academic research destroy stock return predictability?](https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12365)
- [MindStudio: AI trading agent with Claude Code and Alpaca](https://www.mindstudio.ai/blog/build-ai-trading-agent-claude-code-alpaca) and [Humbled Trader: AI trading bot with Claude and Interactive Brokers](https://www.humbledtrader.com/blog/ai-trading-bot-claude-ibkr/)
- GitHub: [QuantConnect/mcp-server](https://github.com/QuantConnect/mcp-server), [QuantConnect/lean-cli](https://github.com/QuantConnect/lean-cli), [tradermonty/claude-trading-skills](https://github.com/tradermonty/claude-trading-skills), [shakeebshaan/claude-code-quant-skills](https://github.com/shakeebshaan/claude-code-quant-skills), [esvhd/pypbo](https://github.com/esvhd/pypbo), [gnzsnz/ib-gateway-docker](https://github.com/gnzsnz/ib-gateway-docker), [wilsonfreitas/awesome-quant](https://github.com/wilsonfreitas/awesome-quant)
- [IBC user guide: unattended IB Gateway](https://github.com/IbcAlpha/IBC/blob/master/userguide.md)

Source: the published page at https://claude.ai/artifact/LJigDUw3WEeNkCCe5C3Yow. This Markdown copy was generated from it on 18 September 2026.
