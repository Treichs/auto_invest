# Research log

One row per backtest run, appended before the result is looked at. Phase 3 counts the rows; the count sets the bar for the Deflated Sharpe Ratio, so never delete a row. Hold-out is 2025-01-01 onward ([ADR 0017](adr/0017-hold-out-period-from-2025.md)); a run with an end date in the hold-out does not belong here and must not be made.

Columns: the rubric hash is the first eight characters the backtest logs at start; trades, net return, and max drawdown come from the backtest Overview; the top check is the largest count in the `rejections` log line.

| Date | Year | What changed | Rubric hash | Trades | Net return after costs | Max drawdown | Top rejecting check (count) |
|---|---|---|---|---|---|---|---|
| 2026-09-19 | 2019 | baseline | be9e47fe | 98 | -0.18% | 1.6% | trade_beats_its_costs (27,701) |
| 2026-09-19 | 2020 | none, same code as the baseline | be9e47fe | 199 | -6.23% | 6.5% | trade_beats_its_costs (23,365) |

Known defect in the 2020 run: 2020-11-27 was a half day (market closed 13:00). The forced close is scheduled at 15:50, so the QQQ position opened at 10:25 was not closed; its stop was cancelled at 15:50 and the close order filled at Monday's open. The position was held over the weekend without a stop. Early-close days need handling before any later run counts toward Phase 3.
