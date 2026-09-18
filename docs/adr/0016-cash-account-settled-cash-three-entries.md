# 0016. Cash account: settled cash only, three entries a day

**Status**: Accepted
**Date**: 2026-09-18

## Context
In a cash account, sale proceeds settle the next business day, so each dollar can be used once a day. With a 25% position cap that allows three entries. Buying with unsettled money can restrict the account for 90 days.

## Decision
The rubric checks settled cash before every entry and caps entries at three a day. Research and paper trading run under the same rule.

## Consequences
The 80% total cap can never bind while entries are capped at three. A margin account, USD 2,000 minimum, is a later loosening that goes through backtest and paper first.
