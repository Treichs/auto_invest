# Research log

One row per backtest run, appended before the result is looked at. Phase 3 counts the rows; the count sets the bar for the Deflated Sharpe Ratio, so never delete a row. Hold-out is 2025-01-01 onward ([ADR 0017](adr/0017-hold-out-period-from-2025.md)); a run with an end date in the hold-out does not belong here and must not be made.

Columns: the rubric hash is the first eight characters the backtest logs at start; trades, net return, and max drawdown come from the backtest Overview; the top check is the largest count in the `rejections` log line.

| Date | Year | What changed | Rubric hash | Trades | Net return after costs | Max drawdown | Top rejecting check (count) |
|---|---|---|---|---|---|---|---|
| 2026-09-19 | 2019 | baseline | be9e47fe | 98 | -0.18% | 1.6% | trade_beats_its_costs (27,701) |
