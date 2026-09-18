# 0005. Research engine is LEAN on the QuantConnect free plan

**Status**: Accepted
**Date**: 2026-09-18

## Context
Backtests with clean data usually cost money. The QuantConnect free plan gives unlimited cloud backtests with data included, but no local tool and no custom packages.

## Decision
All research and backtesting runs on the QuantConnect free plan.

## Consequences
Rubric files are pasted into the web editor, so they stay small and free of third-party imports. Nothing is paid for.
