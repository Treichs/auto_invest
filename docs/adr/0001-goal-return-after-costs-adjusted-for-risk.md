# 0001. Goal is return after costs, adjusted for risk

**Status**: Accepted
**Date**: 2026-09-18

## Context
A goal such as "highest daily profit" rewards whatever fitted the past best, and the past is easy to fit by accident.

## Decision
The system optimises return after commissions, spread, and slippage, judged against the risk taken.

## Consequences
Every backtest includes real costs. Stage gates use out-of-sample and overfitting statistics, never a headline return.
