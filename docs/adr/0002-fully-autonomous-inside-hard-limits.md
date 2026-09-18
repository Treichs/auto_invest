# 0002. Fully autonomous inside hard limits

**Status**: Accepted
**Date**: 2026-09-18

## Context
The owner wants a system that trades without being asked, but not one that can decide its own limits.

## Decision
The system places trades on its own. Limits sit in a separate risk layer and a ceilings file that the strategy cannot change.

## Consequences
No trade needs approval. Loosening any limit is a human change that goes back through the stage gates.
