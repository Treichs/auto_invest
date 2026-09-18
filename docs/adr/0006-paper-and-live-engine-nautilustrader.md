# 0006. Paper and live engine is NautilusTrader, self-hosted

**Status**: Accepted
**Date**: 2026-09-18

## Context
Running LEAN live needs a paid seat, about $60 a month, which on a $5,000 account fails the cost test. NautilusTrader is free, has an Interactive Brokers adapter, and its risk engine sits outside the strategy.

## Decision
NautilusTrader, version pinned, runs paper and live trading in Docker on a small cloud server.

## Consequences
The rubric is ported once, in Phase 4, and both engines must agree before paper trading starts.
