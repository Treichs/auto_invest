# 0013. First dashboard is Grafana, view only

**Status**: Accepted
**Date**: 2026-09-18

## Context
The paper gate needs a status board within an afternoon, not a front-end project.

## Decision
Grafana in its own container, reading Postgres through a read-only role, reached only over a private network or tunnel.

## Consequences
No trade or settings controls exist on the board. Panels are arranged, not coded, and are provisioned from files in the repo.
