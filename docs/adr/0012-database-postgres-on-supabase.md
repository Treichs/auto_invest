# 0012. Database hub is Postgres, hosted on Supabase

**Status**: Accepted
**Date**: 2026-09-18

## Context
NautilusTrader has no dashboard. Any screen needs history, and the engine must never be reachable from a screen.

## Decision
One Postgres database, hosted on the Supabase free plan, sits between the engine and every screen. The engine writes; screens read.

## Consequences
The engine does not depend on the database: if it is unreachable, trading continues and rows queue locally. Broker credentials are never stored in it.
