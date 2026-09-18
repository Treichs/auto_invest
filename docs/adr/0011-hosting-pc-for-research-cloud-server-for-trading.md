# 0011. Research on the PC, paper and live on a small cloud server

**Status**: Accepted
**Date**: 2026-09-18

## Context
A home PC sleeps, updates, and drops connections. A trading system must be awake for the whole market day.

## Decision
Research and development on the PC. Paper and live trading in Docker on one small Linux cloud server, about $5 to $10 a month.

## Consequences
The server is hardened and reached by key only. Deploys happen only when the market is closed.
