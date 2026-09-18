# 0017. Hold-out period: 1 January 2025 onward

**Status**: Accepted
**Date**: 2026-09-18

## Context
Research tunes the rubric on past data. Any day that was seen while tuning cannot later prove the result is real, so the hold-out must be fixed before the first backtest, not after.

## Decision
Every market day from 2025-01-01 onward is hold-out, open-ended. In-sample data ends 2024-12-31.

## Consequences
Phase 2 backtests may not start on or run past 2024-12-31; the LEAN algorithm refuses an end date in the hold-out. Phase 3 runs the hold-out exactly once. Moving this date is a new decision that supersedes this one.
