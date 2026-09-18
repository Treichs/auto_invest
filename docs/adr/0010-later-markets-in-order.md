# 0010. Later markets wait their turn

**Status**: Accepted
**Date**: 2026-09-18

## Context
Each new market adds an account, an adapter, sizing rules, and cost. Doing them together would delay the first paper test by months.

## Decision
After index ETFs: high relative volume stocks, then crypto on Kraken Pro, then options. Each is its own small project with full stage gates.

## Consequences
The relative volume score component is built now but does its real work only when stocks are added.
